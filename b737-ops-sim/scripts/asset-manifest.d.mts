export interface AssetManifestValidationOptions {
  pinnedSha: string;
  repo: string;
  license: string;
  requiredPaths: string[];
}

export type AssetManifestValidation = { ok: true } | { ok: false; reason: string };

export function validateAssetManifest(
  manifest: unknown,
  options: AssetManifestValidationOptions,
): AssetManifestValidation;
