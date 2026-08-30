// Top-down view, like the Mystery Dungeon games the original was modelled on:
// square tiles on a straight grid, seen from directly above. Nothing is
// extruded, so nothing can hide anything else — the whole occlusion problem the
// quarter view had simply does not exist here.

/** Tile edge in logical px. The map band fits 26 x 11 of these. */
export const TS = 48;
/** Sprite sizes are authored against one tile; kept so call sites read the same. */
export const S = TS / 48;

export const ANIM_MS = 130;
export const CAM_LERP = 0.18;

/** Where a character's feet sit inside its tile: below centre, so the body
 * overlaps the tile above and the grid reads as ground rather than as a chart. */
export const FOOT = TS * 0.34;

export const gx = (x: number): number => x * TS;
export const gy = (y: number): number => y * TS;

/** Eases toward the player instead of snapping cell by cell. */
export class Camera {
  x = 0;
  y = 0;
  private ready = false;

  reset(): void {
    this.ready = false;
  }

  /** First frame, or a jump the eye cannot follow anyway: snap. Otherwise ease. */
  follow(tx: number, ty: number): void {
    if (!this.ready || Math.abs(tx - this.x) + Math.abs(ty - this.y) > TS * 7) {
      this.x = tx;
      this.y = ty;
      this.ready = true;
      return;
    }
    this.x += (tx - this.x) * CAM_LERP;
    this.y += (ty - this.y) * CAM_LERP;
  }

  settled(tx: number, ty: number): boolean {
    return Math.abs(tx - this.x) + Math.abs(ty - this.y) <= 0.5;
  }
}
