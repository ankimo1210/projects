export interface DskyStateMsg {
  type: "dsky_state";
  schema_version: number;
  prog: string; verb: string; noun: string;
  r1: string; r2: string; r3: string;
  lamps: Record<string, boolean>;
  verb_noun_flash: boolean; restart: boolean; standby: boolean;
  key_rel: boolean; opr_err: boolean; temp: boolean;
}
export type ServerMsg = DskyStateMsg | { type: string };

export interface DskyView {
  prog: string; verb: string; noun: string;
  r1: string; r2: string; r3: string;
  lamps: Record<string, boolean>;
  verbNounFlash: boolean; restart: boolean; standby: boolean;
  keyRel: boolean; oprErr: boolean; temp: boolean;
  connected: boolean;
}
