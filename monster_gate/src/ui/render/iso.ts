// Quarter view: 2:1 diamond tiles, walls extruded upward, camera eased.

export const TW = 96;
export const TH = 48;
/** Ground-to-surface thickness of a floor tile; matches the art's own skirt. */
export const FLOOR_H = 8;
export const WALL_H = 40;
/** Sprite sizes were tuned on a 64px-wide tile; scale them with the tile. */
export const S = TW / 64;

export const ANIM_MS = 130;
export const CAM_LERP = 0.18;

export function isoX(x: number, y: number): number {
  return (x - y) * (TW / 2);
}

export function isoY(x: number, y: number): number {
  return (x + y) * (TH / 2);
}

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
    if (!this.ready || Math.abs(tx - this.x) + Math.abs(ty - this.y) > TW * 5.6) {
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
