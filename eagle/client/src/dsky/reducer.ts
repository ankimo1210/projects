import type { DskyView, ServerMsg, DskyStateMsg } from "./types";

export const initialDsky: DskyView = {
  prog: "  ", verb: "  ", noun: "  ",
  r1: "      ", r2: "      ", r3: "      ",
  lamps: {}, verbNounFlash: false, restart: false, standby: false,
  keyRel: false, oprErr: false, temp: false, connected: false,
};

export function reduceServerMsg(state: DskyView, msg: ServerMsg): DskyView {
  if (msg.type !== "dsky_state") return state;
  const m = msg as DskyStateMsg;
  return {
    ...state,
    prog: m.prog, verb: m.verb, noun: m.noun,
    r1: m.r1, r2: m.r2, r3: m.r3,
    lamps: m.lamps,
    verbNounFlash: m.verb_noun_flash, restart: m.restart, standby: m.standby,
    keyRel: m.key_rel, oprErr: m.opr_err, temp: m.temp,
  };
}
