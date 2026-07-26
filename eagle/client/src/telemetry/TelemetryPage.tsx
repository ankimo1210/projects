import { StripChart } from "./StripChart";
import type { TelemetryBuffer } from "./useTelemetryBuffer";

interface Props {
  buffer: TelemetryBuffer;
  sendRod: (up: boolean) => void;
}

function popcount(n: number): number {
  let c = 0;
  for (let i = 0; i < 16; i++) if (n & (1 << i)) c++;
  return c;
}

/**
 * Engineer telemetry board: four strip charts, a numeric panel, the P66
 * phase timeline, and the ROD switch buttons.
 */
export function TelemetryPage({ buffer, sendRod }: Props) {
  const { ring, version, latest, phases } = buffer;
  const frames = ring.frames();

  return (
    <div className="engr">
      <div className="engr-charts">
        <StripChart
          title="Altitude (m)"
          version={version}
          frames={frames}
          series={[{ label: "alt", get: (f) => f.alt_m, color: "#5ad" }]}
        />
        <StripChart
          title="Descent rate (m/s)"
          version={version}
          frames={frames}
          series={[
            { label: "truth vz", get: (f) => f.vz_ms, color: "#5ad" },
            { label: "AGC hdot", get: (f) => f.agc_hdot_ms, color: "#fa5" },
          ]}
        />
        <StripChart
          title="Thrust (N) + jets"
          version={version}
          frames={frames}
          series={[
            { label: "thrust", get: (f) => f.thrust_n, color: "#5d8" },
            { label: "jets", get: (f) => popcount(f.jets), color: "#d58" },
          ]}
        />
        <StripChart
          title="Fuel DPS (kg) + drift (ms)"
          version={version}
          frames={frames}
          series={[
            { label: "fuel dps", get: (f) => f.fuel_dps_kg, color: "#5ad" },
            { label: "drift ms", get: (f) => f.drift_ms, color: "#fa5" },
          ]}
        />
      </div>

      <div className="engr-side">
        <div className="engr-nums">
          <h2>State</h2>
          {latest ? (
            <table>
              <tbody>
                <Row k="MM" v={latest.mm || "—"} />
                <Row k="t" v={latest.t_s.toFixed(1) + " s"} />
                <Row k="alt" v={latest.alt_m.toFixed(1) + " m"} />
                <Row k="vz" v={latest.vz_ms.toFixed(2) + " m/s"} />
                <Row k="v_horiz" v={latest.v_horiz_ms.toFixed(2) + " m/s"} />
                <Row k="tilt" v={latest.tilt_deg.toFixed(1) + "°"} />
                <Row k="mass" v={latest.mass_kg.toFixed(0) + " kg"} />
                <Row k="thrust" v={latest.thrust_n.toFixed(0) + " N"} />
                <Row k="cmd pulses" v={String(latest.throttle_cmd_pulses)} />
                <Row k="nav err alt" v={fmt(latest.nav_err_alt_m, "m")} />
                <Row k="nav err hdot" v={fmt(latest.nav_err_hdot_ms, "m/s")} />
                <Row k="drift" v={latest.drift_ms.toFixed(0) + " ms"} />
                <Row k="downlink" v={latest.downlink_wps.toFixed(0) + " wps"} />
                <Row k="ingest drops" v={String(latest.ingest_drops)} />
                <Row k="handover" v={latest.handover ? "FIRED" : "—"} />
              </tbody>
            </table>
          ) : (
            <p className="muted">waiting for telemetry…</p>
          )}
          {latest?.touchdown && (
            <div className={"td-badge td-" + latest.touchdown.toLowerCase()}>
              TOUCHDOWN: {latest.touchdown}
            </div>
          )}
        </div>

        <div className="engr-rod">
          <h2>Rate of descent</h2>
          <button
            onClick={() => sendRod(false)}
            title="ch016 bit7 — descend faster (−1 ft/s target)"
          >
            ROD −1 ft/s
          </button>
          <button
            onClick={() => sendRod(true)}
            title="ch016 bit6 — descend slower (+1 ft/s target)"
          >
            ROD +1 ft/s
          </button>
        </div>

        <div className="engr-phases">
          <h2>Phases</h2>
          <ul>
            {[...phases].reverse().map((p, i) => (
              <li key={i}>
                <span className="ph-mm">P{p.mm}</span>
                <span className="ph-t">{p.t_s.toFixed(1)} s</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <tr>
      <td className="k">{k}</td>
      <td className="v">{v}</td>
    </tr>
  );
}

function fmt(x: number | null, unit: string): string {
  return x === null ? "—" : x.toFixed(2) + " " + unit;
}
