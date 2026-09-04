// A deterministic, linear-light Radiance HDR: four rectangular studio softboxes.
// Both engines consume these exact bytes, with no remote environment assets.
export function createStudioHdr() {
  const width = 512;
  const height = 256;
  const header = Buffer.from(
    `#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y ${height} +X ${width}\n`,
  );
  const pixels = Buffer.alloc(width * height * 4);
  const panels = [
    { axis: 1, plane: 5, center: [0, 5, -3], half: [5, 0, 1], rgb: [5, 5, 5] },
    {
      axis: 0,
      plane: -4,
      center: [-4, 1, 3],
      half: [0, 3.5, 1],
      rgb: [4, 4, 4],
    },
    { axis: 0, plane: 4, center: [4, 3, 2], half: [0, 3, 1.5], rgb: [3, 3, 3] },
    {
      axis: 1,
      plane: -4,
      center: [0, -4, 1],
      half: [4, 0, 1.5],
      rgb: [0.89, 1.5, 0.2],
    },
  ];
  for (let y = 0; y < height; y++) {
    const theta = ((y + 0.5) / height) * Math.PI;
    for (let x = 0; x < width; x++) {
      const phi = ((x + 0.5) / width - 0.5) * 2 * Math.PI;
      const ray = [
        Math.cos(phi) * Math.sin(theta),
        Math.cos(theta),
        Math.sin(phi) * Math.sin(theta),
      ];
      let rgb = [0.025, 0.03, 0.025];
      let nearest = Infinity;
      for (const panel of panels) {
        const t = panel.plane / ray[panel.axis];
        if (t <= 0 || t >= nearest) continue;
        if (
          ray.every(
            (component, axis) =>
              axis === panel.axis ||
              Math.abs(component * t - panel.center[axis]) <= panel.half[axis],
          )
        ) {
          rgb = panel.rgb;
          nearest = t;
        }
      }
      const exponent = Math.floor(Math.log2(Math.max(...rgb))) + 1;
      const scale = 256 / 2 ** exponent;
      const offset = (y * width + x) * 4;
      for (let channel = 0; channel < 3; channel++)
        pixels[offset + channel] = Math.floor(rgb[channel] * scale);
      pixels[offset + 3] = exponent + 128;
    }
  }
  // Old-style flat RGBE scanlines are supported by both official HDR loaders.
  return Buffer.concat([header, pixels]);
}
