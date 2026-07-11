<script setup lang="ts">
// One component per row = one render effect per row. When a reactive
// quote's field mutates, ONLY this row's effect re-runs — Vue gives the
// granularity by default that React needed an external store for.
import { onBeforeUpdate, onMounted } from 'vue';
import type { Quote, PerfMeter } from '@rosetta/core';

const props = defineProps<{ q: Quote; perf: PerfMeter }>();
onMounted(() => props.perf.countWork(1));
onBeforeUpdate(() => props.perf.countWork(1)); // work = row updates
</script>

<template>
  <tr>
    <td class="sym">{{ q.symbol }}</td>
    <td :class="q.dir === 1 ? 'up' : q.dir === -1 ? 'down' : ''">
      {{ q.dir === 1 ? '▲ ' : q.dir === -1 ? '▼ ' : '' }}{{ q.last.toFixed(2) }}
    </td>
    <td>{{ q.bid.toFixed(2) }}</td>
    <td>{{ q.ask.toFixed(2) }}</td>
    <td :class="q.changePct >= 0 ? 'up' : 'down'">
      {{ q.changePct >= 0 ? '+' : '' }}{{ q.changePct.toFixed(2) }}%
    </td>
  </tr>
</template>
