import { CARDS } from "../engine/cards";
import { ENEMY } from "../engine/dungeon-def";
import type { DungeonState, Event } from "../engine/types";

function enemyName(state: DungeonState, id: number): string {
  const e = state.enemies.find((x) => x.id === id);
  return e ? ENEMY[e.kind].name : "敵";
}

/** Human-readable log lines for events; `after` is the state the events produced. */
export function describe(events: Event[], before: DungeonState, after: DungeonState): string[] {
  const out: string[] = [];
  const name = (id: number) => enemyName(before, id) ?? enemyName(after, id);
  for (const e of events) {
    switch (e.t) {
      case "attack":
        if (e.by === "player") out.push(`${name(e.target as number)}に${e.dmg}ダメージ${e.crit ? "（会心）" : ""}`);
        else out.push(`${name(e.by)}の${e.ranged ? "射撃" : "攻撃"}: ${e.dmg}ダメージ`);
        break;
      case "died":
        out.push(`${ENEMY[e.kind].name}を倒した`);
        break;
      case "grow":
        out.push(`レベルアップ! (+${e.level}) HP+${e.hp} ATK+${e.atk} DEF+${e.def}`);
        break;
      case "pickup":
        out.push(`${CARDS[e.card].name}を拾った`);
        break;
      case "pickupWin":
        out.push(`WIN +${e.amount}`);
        break;
      case "handFull":
        out.push(`手札がいっぱいで${CARDS[e.card].name}を拾えない`);
        break;
      case "cardUsed":
        out.push(`${CARDS[e.card].name}を使った (MP-${e.mpCost})`);
        break;
      case "notEnoughMp":
        out.push(`MPが足りない（${CARDS[e.card].name}: ${e.need}）`);
        break;
      case "discarded":
        out.push(`${CARDS[e.card].name}を捨てた (MP+${e.mpBack})`);
        break;
      case "roomEntered":
        if (e.hpGain || e.mpGain) out.push(`新しい部屋: HP+${e.hpGain} MP+${e.mpGain}`);
        break;
      case "floorChanged":
        out.push(`--- ${e.floorNo}F ---`);
        break;
      case "spawn":
        out.push(`${ENEMY[e.kind].name}が現れた`);
        break;
      case "enemySlept":
        out.push(`${name(e.enemyId)}は眠った`);
        break;
      case "enemyConfused":
        out.push(`${name(e.enemyId)}は混乱した`);
        break;
      case "bossDrop":
        out.push(`ボスが${CARDS[e.card].name}を落とした！`);
        break;
      case "revived":
        out.push(`リバイブリングの力で復活！ HP ${e.hp}`);
        break;
      case "acid":
        break;
      case "summoned":
        out.push(`${ENEMY[e.kind].name}を召喚した`);
        break;
      case "allyHit":
        out.push(`召喚モンスターが${name(e.target)}に${e.dmg}ダメージ`);
        break;
      case "allyHurt":
        break;
      case "allyDied":
        out.push(`召喚した${ENEMY[e.kind].name}が倒された`);
        break;
      case "doubleUp":
        out.push(`ダブルアップ！ クリア配当 ×${e.multiplier}`);
        break;
      case "bought":
        out.push(`${CARDS[e.card].name}を買った (WIN-${e.price})`);
        break;
      case "spun":
        out.push(e.payout > 0 ? `スロット: ${e.payout}枚！` : "スロット: はずれ");
        break;
      case "slide":
        break;
      case "playerDied":
        out.push("倒れた…");
        break;
      case "cleared":
        out.push(`クリアの証を手に入れた！ WIN ${e.win}`);
        break;
      case "escaped":
        out.push(`脱出した。WIN ${e.win}`);
        break;
      case "blocked":
        if (e.reason === "no target") out.push("対象がいない");
        else if (e.reason === "not on stairs") out.push("階段の上でしか使えない");
        else if (e.reason === "not on altar") out.push("祭壇の上でしか使えない");
        else if (e.reason === "already used") out.push("もう使っている");
        else if (e.reason === "not enough win") out.push("WINが足りない");
        else if (e.reason === "hand full") out.push("手札がいっぱい");
        else if (e.reason === "sold out") out.push("売り切れ");
        else if (e.reason === "out of order") out.push("スロットは動かなくなった");
        else if (e.reason === "too many summons") out.push("これ以上は召喚できない");
        break;
      case "log":
        out.push(e.msg);
        break;
      default:
        break;
    }
  }
  return out;
}
