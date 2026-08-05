import { vSpeedsForWeight, type AircraftState } from '@b737/shared';
import type { TrainingSession } from '@b737/training-engine';

/** One small objective for the beginner-facing mission coach. */
export interface GuidanceHint {
  /** Stable while the same objective is active; drives completion feedback. */
  id: string;
  controlId: string | null;
  target: 'control' | 'checklist' | 'radio' | 'systems' | 'fms' | 'cockpit' | 'debrief';
  title: string;
  text: string;
  detail: string;
  success: string;
  metrics: { label: string; value: string; tone?: 'good' | 'warn' }[];
}

const CONTROL_LABELS: Record<string, string> = {
  throttle: 'THROTTLE',
  reverse_thrust: 'REVERSE',
  flaps: 'FLAPS',
  speedbrake: 'SPD BRK',
  speedbrake_arm: 'SPD BRK ARM',
  gear: 'GEAR',
  autobrake: 'AUTOBRAKE',
  parking_brake: 'PARK',
  light_landing: 'LAND light',
  light_taxi: 'TAXI light',
  light_beacon: 'BEACON',
};

/**
 * Guided-mode mission derivation. Priority is deliberately strict:
 * unanswered radio → active checklist item → current flight phase.
 */
export function deriveGuidance(session: TrainingSession): GuidanceHint {
  const state = session.state;
  const pending = session.transcript.find((e) => e.expectedResponse && !e.responseResult);
  if (pending) {
    return {
      id: `radio:${pending.id}`,
      controlId: null,
      target: 'radio',
      title: `${pending.speaker === 'atc' ? 'ATC' : '副操縦士'}に返答する`,
      text: 'ATC / Crew欄の青い選択肢から、聞こえた内容と同じ返答を選びます。',
      detail: `受信内容: “${pending.message}”`,
      success: '返答の横に「✓ readback」が出れば完了です。',
      metrics: [],
    };
  }

  const checklistId = session.activeChecklistId;
  if (checklistId) {
    const run = session.runtime.checklistRuns.get(checklistId);
    const item = run?.activeItem;
    if (item) {
      if (item.definition.id === 'flight_controls') {
        const progress = session.flightControlCheckProgress;
        const metric = (label: string, complete: boolean) => ({
          label,
          value: complete ? '✓ DONE' : 'PRESS',
          tone: complete ? ('good' as const) : ('warn' as const),
        });
        return {
          id: `checklist:${checklistId}:flight_controls`,
          controlId: null,
          target: 'cockpit',
          title: `${run!.definition.title}: Flight controls`,
          text: '3D画面をクリックし、← → ↑ ↓ , . を1回ずつ押します。下の6項目を緑にしてからVerifyします。',
          detail:
            '短いキー入力でも記録されます。キーを押している間だけヨーク／ラダーが動き、離すと中央へ戻ります。',
          success: 'ROLL・PITCH・RUDDERの左右／前後がすべて「✓ DONE」になれば完了です。',
          metrics: [
            metric('ROLL ←', progress.rollLeft),
            metric('ROLL →', progress.rollRight),
            metric('PITCH ↑', progress.pitchForward),
            metric('PITCH ↓', progress.pitchBack),
            metric('RUDDER ,', progress.rudderLeft),
            metric('RUDDER .', progress.rudderRight),
          ],
        };
      }
      const controlId = checklistControl(item.definition.id, state);
      const label = controlId ? controlLabel(controlId) : null;
      return {
        id: `checklist:${checklistId}:${item.definition.id}:${controlId ?? 'verify'}`,
        controlId,
        target: controlId?.startsWith('system:') ? 'systems' : controlId ? 'control' : 'checklist',
        title: `${run!.definition.title}: ${item.definition.challenge}`,
        text: label
          ? `点滅している「${label}」を操作し、正しい状態にします。`
          : '機体の状態を確認して、チェックリストの「Verify」を押します。',
        detail:
          item.definition.trainingHint ??
          `期待する状態: ${item.dynamicResponseValue ?? item.definition.response ?? 'Checked'}`,
        success: `表示が「${item.dynamicResponseValue ?? item.definition.response ?? 'Checked'}」になり、項目に✓が付けば完了です。`,
        metrics: checklistMetrics(item.definition.id, state),
      };
    }
  }

  return phaseGuidance(session.phaseId, state, session.scenario.initialState.grossWeightLb);
}

function phaseGuidance(
  phase: string,
  state: AircraftState | null,
  grossWeightLb: number,
): GuidanceHint {
  const flight = flightMetrics(state);
  switch (phase) {
    case 'cold_and_dark':
      return mission(
        phase,
        'system:battery',
        'systems',
        '機体に電源を入れる',
        'Systemsを開き、ELEC欄のBATをONにします。',
        'バッテリーがDC busへ最初の電源を供給します。',
        'DC busがPOWEREDになれば次へ進みます。',
        [{ label: 'DC BUS', value: state?.systems.electrical.dcBusPowered ? 'POWERED' : 'OFF' }],
      );
    case 'power_on':
      return powerOnGuidance(state);
    case 'apu_available':
      return mission(
        phase,
        'system:apu_gen',
        'systems',
        'APU電源と始動準備を整える',
        'APU GEN、燃料ポンプ、APU BLEEDを設定し、Before StartをVerifyします。',
        'エンジン始動にはAC電源、燃料圧、25 psi以上のダクト圧が必要です。',
        'Before Start (systems)がすべて✓になれば完了です。',
        systemMetrics(state),
      );
    case 'engine_start':
      return engineStartGuidance(state);
    case 'after_start':
      return mission(
        phase,
        'system:gen1',
        'systems',
        'After Start構成にする',
        '両GEN、PACK、HYD pumpをON、APU BLEEDをOFFにしてVerifyします。',
        'エンジン側の電源・空気・油圧へ切り替える手順です。',
        'After Startチェックリストがすべて✓になれば完了です。',
        systemMetrics(state),
      );
    case 'ready_to_taxi':
      return mission(
        phase,
        null,
        'radio',
        'タクシー許可をもらう',
        'ATC / Crew欄の「Request taxi clearance」を押します。',
        '許可と経路を復唱してからブレーキを解除します。',
        '正しいreadback後、ゆっくり動き始めるとTaxi outへ進みます。',
        flight,
      );
    case 'preflight':
      return mission(
        phase,
        null,
        'checklist',
        '出発準備を完了する',
        'Before Startを上から順にVerifyし、次にタクシー許可を要求します。',
        'チェックリストは実際の機体状態を検証します。',
        '全項目が緑の✓になれば次へ進めます。',
        flight,
      );
    case 'taxi_out':
      return mission(
        phase,
        'throttle',
        'control',
        '滑走路28R手前までタクシーする',
        'PARKを解除し、THROTTLEを少し上げてTaxiway Aを進みます。',
        '地上速度は20 kt以下、hold line手前で停止します。',
        '28Rのholding positionで停止するとHold shortへ進みます。',
        flight,
      );
    case 'hold_short':
    case 'before_takeoff':
      return mission(
        phase,
        null,
        'checklist',
        '離陸許可を準備する',
        'Before Takeoffを完了し、「Request takeoff clearance」を押します。',
        '正しいreadbackが終わるまで滑走路へ入りません。',
        '許可後に動き出すとLine upへ進みます。',
        flight,
      );
    case 'line_up':
      return mission(
        phase,
        null,
        'cockpit',
        '滑走路中心線に整列する',
        '28Rへ進入し、heading約284°でセンターラインに合わせます。',
        'ラダー／ヨークでゆっくり修正します。',
        '40 ktを超えるとTakeoff roll判定へ進みます。',
        flight,
      );
    case 'takeoff_roll': {
      const vr = vSpeedsForWeight(grossWeightLb).vrKt;
      return mission(
        phase,
        'throttle',
        'control',
        '離陸する',
        `THROTTLEを離陸位置へ。IAS ${Math.round(vr)} ktでゆっくり機首を上げます。`,
        'センターラインを保ち、VR前に急な引き起こしをしません。',
        'IAS 100 kt超かつpitch 2.5°超でRotationへ進みます。',
        state
          ? [
              { label: 'IAS', value: `${state.speeds.iasKt.toFixed(0)} kt` },
              { label: 'VR', value: `${Math.round(vr)} kt` },
              { label: 'HDG', value: `${state.attitude.headingDegMag.toFixed(0)}°` },
            ]
          : [],
      );
    }
    case 'rotation':
      return mission(
        phase,
        null,
        'cockpit',
        '上昇姿勢を作る',
        '↓キーで機首を約15°まで上げ、正の上昇率を作ります。',
        '姿勢を急に変えず、radio altitudeが増えることを確認します。',
        '離陸してV/Sが+300 fpmを超えるとInitial climbへ進みます。',
        flight,
      );
    case 'initial_climb': {
      const gearDown = state?.controls.gearLeverDown ?? true;
      return mission(
        phase,
        gearDown ? 'gear' : null,
        gearDown ? 'control' : 'cockpit',
        gearDown ? 'Positive rate — GEAR UP' : 'ATCベクターを飛ぶ',
        gearDown
          ? '上昇を確認したら、点滅するGEARのUPを押します。'
          : 'ATCのheading/altitudeをMCPへ設定し、パターンを飛びます。',
        'ギア格納後はATCの指示とPFDのFlight Directorを追います。',
        'Approach clearanceを正しく復唱するとApproach setupへ進みます。',
        flight,
      );
    }
    case 'approach_setup':
      return mission(
        phase,
        'flaps',
        'control',
        '着陸形態を作る',
        'FLAPS、GEAR、SPD BRK ARM、AUTOBRAKEを順に設定します。',
        '速度を落としながらLocalizerとGlideslopeへ会合します。',
        'LOC ±1 dot、RA 2500 ft未満でFinal approachへ進みます。',
        approachMetrics(state),
      );
    case 'final_approach':
      return mission(
        phase,
        null,
        'cockpit',
        'ILSを安定して追う',
        'PFDのLOC/GSを中央に保ち、Landing checklistを完了します。',
        '1000 ftと500 ftの安定条件を外したらGo Aroundを選べます。',
        'RA 60 ftでLandingフェーズへ進みます。',
        approachMetrics(state),
      );
    case 'go_around':
      return mission(
        phase,
        'gear',
        'control',
        'Go-aroundを確立する',
        'TO/GA thrust、GEAR UP、FLAPS 15で3000 ftへ上昇します。',
        'ATCの新しいベクターを復唱して追います。',
        'RA 1500 ftを超えると再度Approach setupへ戻ります。',
        flight,
      );
    case 'landing':
      return mission(
        phase,
        'reverse_thrust',
        'control',
        '安全に減速する',
        '接地後にREVERSEとブレーキを使い、センターラインを保ちます。',
        '速度が落ちたらreverseを戻し、高速出口へ向かいます。',
        '滑走路を出るとRunway exitへ進みます。',
        flight,
      );
    case 'runway_exit':
      return mission(
        phase,
        'flaps',
        'control',
        '滑走路をクリーンアップする',
        'FLAPS UP、SPD BRK DOWN、LAND light OFFを確認してVerifyします。',
        '停止せず安全なtaxi speedまで減速します。',
        'After Landingがすべて✓になると次へ進みます。',
        flight,
      );
    case 'taxi_in':
      return mission(
        phase,
        'throttle',
        'control',
        'スタンドへ戻る',
        'Taxiway Aを通り、低速で指定スタンドへ進みます。',
        '旋回時は10 kt前後まで落とします。',
        'スタンド付近で停止するとParkedへ進みます。',
        flight,
      );
    case 'parked':
      return mission(
        phase,
        'parking_brake',
        'control',
        '駐機を完了する',
        'PARKをセットし、Shutdown checklistを実行します。',
        '機体を確実に停止してからエンジンと電源を処理します。',
        'Shutdown完了後にDebriefが開きます。',
        flight,
      );
    default:
      return mission(
        phase,
        null,
        'debrief',
        'フライトを振り返る',
        'Debriefでスコアとタイムラインを確認します。',
        '赤・黄の項目から次に練習する操作を1つ選びます。',
        'ResetまたはScenario選択で次のフライトを開始できます。',
        flight,
      );
  }
}

function powerOnGuidance(state: AircraftState | null): GuidanceHint {
  if (!state?.systems.electrical.standbyPowerOn) {
    return mission(
      'power_on:standby',
      'system:standby_power',
      'systems',
      'Standby PowerをONにする',
      'SystemsのELEC欄でSTBYを押します。',
      '主電源系統を失った場合の待機電源を準備します。',
      'STBYが緑になれば次へ進みます。',
      systemMetrics(state),
    );
  }
  if (state.systems.irs.leftState === 'off' || state.systems.irs.rightState === 'off') {
    const side = state.systems.irs.leftState === 'off' ? 'irs_left' : 'irs_right';
    return mission(
      `power_on:${side}`,
      `system:${side}`,
      'systems',
      'IRSをNAVへ入れる',
      `SystemsのIRS欄で${side === 'irs_left' ? 'L NAV' : 'R NAV'}を押します。`,
      '整列には時間がかかるため、APU始動前に開始します。',
      '左右ともALIGNINGまたはALIGNEDになれば次へ進みます。',
      systemMetrics(state),
    );
  }
  if (state.systems.apu.state === 'starting') {
    return mission(
      'power_on:apu_wait',
      null,
      'systems',
      'APU始動を待つ',
      '操作せず、APU N1が上がるのを待ちます。',
      'APUは自動で加速し、発電機が利用可能になります。',
      'APU RUNNINGになれば次へ進みます。',
      systemMetrics(state),
    );
  }
  return mission(
    'power_on:apu_start',
    null,
    'systems',
    'APUを始動する',
    'APU欄のMASTERを1回、続けてSTARTを1回押します。',
    'MASTERだけでは始動しません。DC電源がある状態でSTARTが必要です。',
    'APU表示がSTARTINGになれば、加速を待ちます。',
    systemMetrics(state),
  );
}

function engineStartGuidance(state: AircraftState | null): GuidanceHint {
  if (!state) {
    return mission(
      'engine_start',
      null,
      'systems',
      'エンジンを始動する',
      'Systemsを開きます。',
      '',
      '',
      [],
    );
  }
  for (const [engine, number] of [
    ['left', 1],
    ['right', 2],
  ] as const) {
    const system = state.systems.engines[engine];
    if (system.running) continue;
    if (system.startMode !== 'ground') {
      return mission(
        `engine_start:${engine}:ground`,
        `system:start_${engine}_ground`,
        'systems',
        `Engine ${number}: starterをGNDへ`,
        `ENG START ${number}のGNDを押します。`,
        'APU bleedのダクト圧でN2を回します。',
        'N2が上昇し始めたら次の指示を待ちます。',
        engineMetrics(state, engine),
      );
    }
    if (system.n2Pct < 20) {
      return mission(
        `engine_start:${engine}:wait_n2`,
        null,
        'systems',
        `Engine ${number}: N2を待つ`,
        'N2が20%以上になるまで燃料を入れずに待ちます。',
        '先に燃料を入れるとhot startの原因になります。',
        'N2 20%以上で次の指示へ進みます。',
        engineMetrics(state, engine),
      );
    }
    if (!system.fuelValveOpen) {
      return mission(
        `engine_start:${engine}:fuel`,
        `system:start_lever_${engine}`,
        'systems',
        `Engine ${number}: Start Leverを上げる`,
        `START LEVERS欄のENG ${number}を押して燃料を入れます。`,
        'N2が十分にある状態で点火・燃料供給を開始します。',
        'N2が約62%で安定しRUNNINGになれば完了です。',
        engineMetrics(state, engine),
      );
    }
    return mission(
      `engine_start:${engine}:stabilise`,
      null,
      'systems',
      `Engine ${number}: 安定を待つ`,
      '操作せずN2とoil pressureの上昇を確認します。',
      'starterは安定後に自動で切れます。',
      'RUNNINGになれば次のエンジンへ進みます。',
      engineMetrics(state, engine),
    );
  }
  return mission(
    'engine_start:done',
    null,
    'systems',
    '両エンジン始動完了',
    '次の状態更新を待ちます。',
    '',
    'After Startへ進みます。',
    systemMetrics(state),
  );
}

function checklistControl(itemId: string, state: AircraftState | null): string | null {
  switch (itemId) {
    case 'battery':
      return state?.systems.electrical.batterySwitchOn ? null : 'system:battery';
    case 'standby_power':
      return state?.systems.electrical.standbyPowerOn ? null : 'system:standby_power';
    case 'irs':
      if (state?.systems.irs.leftState === 'off') return 'system:irs_left';
      if (state?.systems.irs.rightState === 'off') return 'system:irs_right';
      return null;
    case 'apu_generator':
      return state?.systems.electrical.acBus1Powered ? null : 'system:apu_gen';
    case 'fuel_pumps':
      if (!state?.systems.fuel.pumpLeftOn) return 'system:fuel_pump_left';
      if (!state.systems.fuel.pumpRightOn) return 'system:fuel_pump_right';
      return null;
    case 'packs_off':
      if (state?.systems.pneumatic.packLeftOn) return 'system:pack_left';
      if (state?.systems.pneumatic.packRightOn) return 'system:pack_right';
      return null;
    case 'apu_bleed':
      return (state?.systems.pneumatic.ductPressurePsi ?? 0) >= 25 ? null : 'system:bleed_apu';
    case 'generators':
      if (!state?.systems.electrical.gen1On) return 'system:gen1';
      if (!state.systems.electrical.gen2On) return 'system:gen2';
      return null;
    case 'apu_bleed_off':
      return state?.systems.apu.bleedOn ? 'system:bleed_apu' : null;
    case 'packs_on':
      if (!state?.systems.pneumatic.packLeftOn) return 'system:pack_left';
      if (!state.systems.pneumatic.packRightOn) return 'system:pack_right';
      return null;
    case 'hydraulics':
      if (!state?.systems.hydraulic.engPump1On) return 'system:hyd_pump_eng1';
      if (!state.systems.hydraulic.engPump2On) return 'system:hyd_pump_eng2';
      return null;
    default:
      return (
        {
          flaps: 'flaps',
          autobrake: 'autobrake',
          speedbrake: 'speedbrake',
          speedbrake_armed: 'speedbrake_arm',
          speedbrake_down: 'speedbrake',
          exterior_lights: 'light_landing',
          lights_after_landing: 'light_landing',
          gear: 'gear',
          flaps_up: 'flaps',
          autobrake_off: 'autobrake',
          parking_brake: 'parking_brake',
          parking_brake_released: 'parking_brake',
          parking_brake_set: 'parking_brake',
          taxi_light: 'light_taxi',
          beacon: 'light_beacon',
          flaps_takeoff: 'flaps',
          thrust_idle: 'throttle',
          exterior_lights_off: 'light_landing',
        }[itemId] ?? null
      );
  }
}

function mission(
  id: string,
  controlId: string | null,
  target: GuidanceHint['target'],
  title: string,
  text: string,
  detail: string,
  success: string,
  metrics: GuidanceHint['metrics'],
): GuidanceHint {
  return { id, controlId, target, title, text, detail, success, metrics };
}

function controlLabel(id: string): string {
  if (id.startsWith('system:'))
    return id.slice('system:'.length).replaceAll('_', ' ').toUpperCase();
  return CONTROL_LABELS[id] ?? id.replaceAll('_', ' ').toUpperCase();
}

function flightMetrics(state: AircraftState | null): GuidanceHint['metrics'] {
  if (!state) return [];
  return [
    { label: 'IAS', value: `${state.speeds.iasKt.toFixed(0)} kt` },
    { label: 'ALT', value: `${state.position.radioAltitudeFt.toFixed(0)} ft` },
    { label: 'V/S', value: `${state.speeds.verticalSpeedFpm.toFixed(0)} fpm` },
  ];
}

function approachMetrics(state: AircraftState | null): GuidanceHint['metrics'] {
  if (!state) return [];
  return [
    { label: 'RA', value: `${state.position.radioAltitudeFt.toFixed(0)} ft` },
    {
      label: 'LOC',
      value:
        state.nav.locDeviationDots === null ? '—' : `${state.nav.locDeviationDots.toFixed(1)} dot`,
    },
    {
      label: 'G/S',
      value:
        state.nav.gsDeviationDots === null ? '—' : `${state.nav.gsDeviationDots.toFixed(1)} dot`,
    },
  ];
}

function systemMetrics(state: AircraftState | null): GuidanceHint['metrics'] {
  if (!state) return [];
  return [
    {
      label: 'APU',
      value: `${state.systems.apu.state.toUpperCase()} ${state.systems.apu.n1Pct.toFixed(0)}%`,
    },
    { label: 'DUCT', value: `${state.systems.pneumatic.ductPressurePsi.toFixed(0)} psi` },
    { label: 'IRS', value: `${(state.systems.irs.alignProgress * 100).toFixed(0)}%` },
  ];
}

function engineMetrics(state: AircraftState, engine: 'left' | 'right'): GuidanceHint['metrics'] {
  const e = state.systems.engines[engine];
  return [
    { label: 'N2', value: `${e.n2Pct.toFixed(0)}%`, tone: e.n2Pct >= 20 ? 'good' : 'warn' },
    { label: 'OIL', value: `${e.oilPressurePsi.toFixed(0)} psi` },
    { label: 'START', value: e.startMode.toUpperCase() },
  ];
}

function checklistMetrics(itemId: string, state: AircraftState | null): GuidanceHint['metrics'] {
  if (!state) return [];
  if (
    [
      'battery',
      'standby_power',
      'irs',
      'apu_generator',
      'fuel_pumps',
      'packs_off',
      'apu_bleed',
      'generators',
      'apu_bleed_off',
      'packs_on',
      'hydraulics',
    ].includes(itemId)
  ) {
    return systemMetrics(state);
  }
  return flightMetrics(state);
}
