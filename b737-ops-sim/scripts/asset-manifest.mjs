import { posix } from 'node:path';

const SHA256_RE = /^[a-f0-9]{64}$/;

/**
 * Validate the trusted shape and required-file contract before any manifest
 * path is joined to the local asset directory.
 */
export function validateAssetManifest(manifest, { pinnedSha, repo, license, requiredPaths }) {
  if (typeof manifest !== 'object' || manifest === null || Array.isArray(manifest)) {
    return { ok: false, reason: 'manifest must be an object' };
  }
  if (manifest.repo !== repo) return { ok: false, reason: 'repository does not match' };
  if (manifest.sha !== pinnedSha) return { ok: false, reason: 'pinned SHA does not match' };
  if (manifest.license !== license) return { ok: false, reason: 'license does not match' };
  if (typeof manifest.fetchedAt !== 'string' || !Number.isFinite(Date.parse(manifest.fetchedAt))) {
    return { ok: false, reason: 'fetchedAt must be an ISO date' };
  }
  if (!Array.isArray(manifest.files) || manifest.files.length === 0) {
    return { ok: false, reason: 'files must be a non-empty array' };
  }

  const paths = new Set();
  for (const file of manifest.files) {
    if (typeof file !== 'object' || file === null || Array.isArray(file)) {
      return { ok: false, reason: 'every file entry must be an object' };
    }
    const path = file.path;
    if (
      typeof path !== 'string' ||
      path.length === 0 ||
      path.startsWith('/') ||
      path.includes('\\') ||
      posix.normalize(path) !== path ||
      path === '..' ||
      path.startsWith('../')
    ) {
      return { ok: false, reason: `unsafe or invalid file path: ${String(path)}` };
    }
    if (paths.has(path)) return { ok: false, reason: `duplicate file path: ${path}` };
    if (!Number.isSafeInteger(file.bytes) || file.bytes <= 0) {
      return { ok: false, reason: `invalid byte size for ${path}` };
    }
    if (typeof file.sha256 !== 'string' || !SHA256_RE.test(file.sha256)) {
      return { ok: false, reason: `invalid sha256 for ${path}` };
    }
    paths.add(path);
  }

  const missing = requiredPaths.filter((path) => !paths.has(path));
  if (missing.length > 0) {
    return { ok: false, reason: `required file missing from manifest: ${missing[0]}` };
  }
  return { ok: true };
}
