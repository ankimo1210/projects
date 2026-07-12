// JavaScript version: the exact same bug compiles nowhere (there is no
// compile step) and only explodes at runtime — or worse, silently produces
// garbage. Try: pnpm --filter @rosetta/core demo:js

function applyDiscount(item, rate) {
  return item.price * (1 - rate);
}

// BUG (intentional): price is a string, rate is a string percentage.
// '1200' * (1 - '10%')  ->  '1200' * NaN  ->  NaN. No error until we try
// to use the result, and even then only because toFixed happens to work
// on NaN ("NaN") — so this LOGS garbage instead of crashing.
const total = applyDiscount({ name: 'book', price: '1200' }, '10%');
console.log('total:', total.toFixed(2)); // "total: NaN" — silent garbage

// A second variant that DOES crash at runtime: typo in the property name.
const item = { name: 'pen', price: 300 };
console.log(item.prise.toFixed(2)); // TypeError: Cannot read properties of undefined
