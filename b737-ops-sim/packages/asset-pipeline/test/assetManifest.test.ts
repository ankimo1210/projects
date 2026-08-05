import { describe, expect, it } from 'vitest';
import { validateAssetManifest } from '../../../scripts/asset-manifest.mjs';

const options = {
  pinnedSha: 'a'.repeat(40),
  repo: 'owner/repo',
  license: 'GPL-2.0',
  requiredPaths: ['Models/cockpit.ac', 'Sounds/Wind.wav'],
};

function file(path: string) {
  return { path, bytes: 42, sha256: 'b'.repeat(64) };
}

function manifest(files: ReturnType<typeof file>[]) {
  return {
    repo: options.repo,
    sha: options.pinnedSha,
    license: options.license,
    fetchedAt: '2026-08-03T00:00:00.000Z',
    files,
  };
}

describe('asset manifest validation', () => {
  it('accepts a complete manifest with unique hashed files', () => {
    expect(validateAssetManifest(manifest(options.requiredPaths.map(file)), options)).toEqual({
      ok: true,
    });
  });

  it('rejects empty and incomplete manifests', () => {
    expect(validateAssetManifest(manifest([]), options)).toMatchObject({ ok: false });
    expect(validateAssetManifest(manifest([file('Models/cockpit.ac')]), options)).toMatchObject({
      ok: false,
      reason: expect.stringContaining('required file missing'),
    });
  });

  it('rejects missing hashes and duplicate paths', () => {
    const missingHash = manifest(options.requiredPaths.map(file));
    missingHash.files[0]!.sha256 = '';
    expect(validateAssetManifest(missingHash, options)).toMatchObject({
      ok: false,
      reason: expect.stringContaining('invalid sha256'),
    });

    const duplicate = manifest([
      file('Models/cockpit.ac'),
      file('Models/cockpit.ac'),
      file('Sounds/Wind.wav'),
    ]);
    expect(validateAssetManifest(duplicate, options)).toMatchObject({
      ok: false,
      reason: expect.stringContaining('duplicate'),
    });
  });

  it('rejects unsafe paths and invalid sizes', () => {
    expect(
      validateAssetManifest(manifest([file('../escape'), file('Sounds/Wind.wav')]), options),
    ).toMatchObject({ ok: false, reason: expect.stringContaining('unsafe') });
    const zeroSize = manifest(options.requiredPaths.map(file));
    zeroSize.files[0]!.bytes = 0;
    expect(validateAssetManifest(zeroSize, options)).toMatchObject({
      ok: false,
      reason: expect.stringContaining('byte size'),
    });
  });
});
