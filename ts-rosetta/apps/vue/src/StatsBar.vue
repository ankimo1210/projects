<script setup lang="ts">
// Isolates the once-per-second sample updates from the board component.
import { onUnmounted, ref } from 'vue';
import type { PerfMeter, PerfSample } from '@rosetta/core';

const props = defineProps<{ perf: PerfMeter }>();
const s = ref<PerfSample | null>(null);
props.perf.onSample = (sample) => (s.value = sample);
onUnmounted(() => (props.perf.onSample = undefined));
</script>

<template>
  <p class="board-stats">
    <span><span data-stat="fps">{{ s?.fps ?? '–' }}</span> fps</span>
    <span><span data-stat="long">{{ s?.longTotal ?? 0 }}</span> long</span>
    <span><span data-stat="upd">{{ s?.updatesPerSec ?? 0 }}</span> upd/s</span>
    <span><span data-stat="work">{{ s?.workPerSec ?? 0 }}</span> work/s</span>
  </p>
</template>
