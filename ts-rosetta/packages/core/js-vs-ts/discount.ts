// TypeScript version: the same bug as discount.js, but the compiler catches it
// BEFORE the code ever runs. Try: pnpm --filter @rosetta/core demo:ts

interface Item {
  name: string;
  price: number;
}

function applyDiscount(item: Item, rate: number): number {
  return item.price * (1 - rate);
}

// BUG (intentional): price passed as a string, rate as a string percentage.
// tsc reports both errors at compile time — this file never reaches runtime.
const total = applyDiscount({ name: 'book', price: '1200' }, '10%');
console.log(total.toFixed(2));
