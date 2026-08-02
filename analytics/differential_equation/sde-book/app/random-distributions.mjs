function clamp(value, low, high) {
  return Math.min(Math.max(value, low), high);
}

export function mulberry32(seed) {
  let value = seed >>> 0;
  return () => {
    value += 0x6d2b79f5;
    let x = value;
    x = Math.imul(x ^ (x >>> 15), x | 1);
    x ^= x + Math.imul(x ^ (x >>> 7), x | 61);
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
  };
}

export function normal(random) {
  const u = Math.max(random(), Number.EPSILON);
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * random());
}

export function poisson(random, mean) {
  if (mean <= 0) return 0;
  if (mean > 32) return Math.max(0, Math.round(mean + Math.sqrt(mean) * normal(random)));
  const threshold = Math.exp(-mean);
  let product = 1;
  let count = 0;
  do {
    count += 1;
    product *= random();
  } while (product > threshold);
  return count - 1;
}

export function binomial(random, trials, probability) {
  const n = Math.max(0, Math.round(trials));
  const p = clamp(probability, 0, 1);
  if (n === 0 || p === 0) return 0;
  if (p === 1) return n;
  if (n <= 48) {
    let count = 0;
    for (let index = 0; index < n; index += 1) if (random() < p) count += 1;
    return count;
  }

  const expectedSuccesses = n * p;
  const expectedFailures = n * (1 - p);
  if (expectedSuccesses < 10) {
    return Math.min(poisson(random, expectedSuccesses), n);
  }
  if (expectedFailures < 10) {
    return n - Math.min(poisson(random, expectedFailures), n);
  }

  const sd = Math.sqrt(n * p * (1 - p));
  return clamp(Math.round(expectedSuccesses + sd * normal(random)), 0, n);
}
