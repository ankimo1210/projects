<script setup lang="ts">
// Vue board: quotes are `reactive` objects mutated IN PLACE per tick.
// The board component itself never re-renders during a run — dependency
// tracking routes each mutation straight to the affected row component.
import { onUnmounted, reactive, ref, shallowRef } from 'vue';
import { TickEngine, PerfMeter, type Quote } from '@rosetta/core';
import BoardRow from './BoardRow.vue';
import StatsBar from './StatsBar.vue';

const SYMBOL_CHOICES = [50, 200, 1000, 5000];
const RATE_CHOICES = [10, 40, 60];
const FRACTION = 0.1;

const symbols = ref(200);
const rate = ref(40);
const running = ref(false);
// shallowRef: the ARRAY is swapped only on (re)start; per-tick reactivity
// lives inside the reactive row objects, not the array.
const quotes = shallowRef<Quote[]>([]);
const perf = new PerfMeter();
let engine: TickEngine | null = null;

function stop() {
  engine?.stop();
  engine = null;
  perf.stop();
  running.value = false;
}

function start() {
  stop();
  const e = new TickEngine({
    symbols: symbols.value,
    rate: rate.value,
    fraction: FRACTION,
    onTick: (updates) => {
      perf.countUpdates(updates.length);
      for (const u of updates) {
        // In-place mutation of a reactive object → only BoardRow updates.
        Object.assign(quotes.value[u.index], {
          last: u.last,
          bid: u.bid,
          ask: u.ask,
          changePct: u.changePct,
          dir: u.dir,
        });
      }
    },
  });
  quotes.value = e.book.map((q) => reactive({ ...q }));
  engine = e;
  e.start();
  perf.start();
  running.value = true;
}

function toggle() {
  if (running.value) stop();
  else start();
}

function setSymbols(n: number) {
  symbols.value = n;
  if (running.value) start(); // restart with new config
}

function setRate(r: number) {
  rate.value = r;
  if (running.value) start();
}

onUnmounted(stop);
</script>

<template>
  <main class="app board">
    <h1>
      Live Board <span class="badge">Vue 3</span>
      <a class="badge" href="#">← tasks</a>
    </h1>

    <section class="row board-controls">
      <span class="stats">work = row updates</span>
    </section>

    <section class="row board-controls">
      <button
        v-for="n in SYMBOL_CHOICES"
        :key="n"
        :data-symbols="n"
        :class="{ on: symbols === n }"
        @click="setSymbols(n)"
      >
        {{ n }}
      </button>
      <span>symbols</span>
      <button
        v-for="r in RATE_CHOICES"
        :key="r"
        :data-rate="r"
        :class="{ on: rate === r }"
        @click="setRate(r)"
      >
        {{ r }}/s
      </button>
      <button data-action="toggle" @click="toggle">{{ running ? 'Stop' : 'Start' }}</button>
    </section>

    <StatsBar :perf="perf" />

    <div v-if="running" class="board-wrap">
      <table class="board-grid">
        <thead>
          <tr>
            <th>Symbol</th>
            <th>Last</th>
            <th>Bid</th>
            <th>Ask</th>
            <th>Chg%</th>
          </tr>
        </thead>
        <tbody>
          <BoardRow v-for="q in quotes" :key="q.symbol" :q="q" :perf="perf" />
        </tbody>
      </table>
    </div>
    <p v-else class="board-idle">Press Start — {{ symbols }} symbols, {{ rate }} ticks/s</p>
  </main>
</template>
