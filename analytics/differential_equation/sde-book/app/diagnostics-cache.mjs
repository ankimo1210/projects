const diagnosticsCache = new WeakMap();

/**
 * Cache deterministic lab diagnostics for the lifetime of an immutable settings object.
 *
 * @template T
 * @param {object} settings
 * @param {string} key
 * @param {() => T} calculate
 * @returns {T}
 */
export function memoizedDiagnostics(settings, key, calculate) {
  let entries = diagnosticsCache.get(settings);
  if (!entries) {
    entries = new Map();
    diagnosticsCache.set(settings, entries);
  }
  if (entries.has(key)) return entries.get(key);
  const result = calculate();
  entries.set(key, result);
  return result;
}
