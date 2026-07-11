<script setup lang="ts">
// Vue: state lives in `ref`s; derived values are `computed` and cache
// automatically. Templates re-render only what depends on changed refs.
import { ref, computed, nextTick } from 'vue';
import {
  type Task,
  type Filter,
  type BenchResult,
  createTask,
  addTask,
  toggleTask,
  deleteTask,
  filterTasks,
  computeStats,
  generateTasks,
  benchmark,
  nextPaint,
  createTasksApi,
} from '@rosetta/core';

type Mode = 'local' | 'api';

interface BenchReport {
  n: number;
  render: BenchResult;
  update: BenchResult;
}

const FILTERS: Filter[] = ['all', 'active', 'done'];

const tasks = ref<Task[]>([]);
const filter = ref<Filter>('all');
const title = ref('');
const mode = ref<Mode>('local');
const apiUrl = ref('http://localhost:4000');
const report = ref<BenchReport | null>(null);
const error = ref<string | null>(null);

const visible = computed(() => filterTasks(tasks.value, filter.value));
const stats = computed(() => computeStats(tasks.value));

async function withApi(fn: () => Promise<void>) {
  try {
    error.value = null;
    await fn();
  } catch (e) {
    error.value = String(e);
  }
}

async function handleAdd() {
  const t = title.value.trim();
  if (!t) return;
  if (mode.value === 'local') {
    tasks.value = addTask(tasks.value, createTask(t));
  } else {
    await withApi(async () => {
      const created = await createTasksApi(apiUrl.value).add(t);
      tasks.value = addTask(tasks.value, created);
    });
  }
  title.value = '';
}

async function handleToggle(task: Task) {
  if (mode.value === 'local') {
    tasks.value = toggleTask(tasks.value, task.id);
  } else {
    await withApi(async () => {
      await createTasksApi(apiUrl.value).setDone(task.id, !task.done);
      tasks.value = toggleTask(tasks.value, task.id);
    });
  }
}

async function handleRemove(id: string) {
  if (mode.value === 'local') {
    tasks.value = deleteTask(tasks.value, id);
  } else {
    await withApi(async () => {
      await createTasksApi(apiUrl.value).remove(id);
      tasks.value = deleteTask(tasks.value, id);
    });
  }
}

async function switchMode(next: Mode) {
  mode.value = next;
  error.value = null;
  if (next === 'api') {
    await withApi(async () => {
      tasks.value = await createTasksApi(apiUrl.value).list();
    });
  } else {
    tasks.value = [];
  }
}

async function runBench(n: number) {
  report.value = null;
  const generated = generateTasks(n);
  // Vue batches DOM updates; `nextTick` resolves after the patch is applied,
  // `nextPaint` after the browser has painted it.
  const render = await benchmark(async () => {
    tasks.value = generated;
    await nextTick();
    await nextPaint();
  });
  const update = await benchmark(async () => {
    tasks.value = tasks.value.map((t) => ({ ...t, done: !t.done }));
    await nextTick();
    await nextPaint();
  });
  report.value = { n, render, update };
}
</script>

<template>
  <main class="app">
    <h1>
      Tasks <span class="badge">Vue 3 + Vite</span>
      <a class="badge" href="#board">board →</a>
    </h1>

    <section class="row">
      <label>
        <input type="radio" :checked="mode === 'local'" @change="switchMode('local')" />
        local state
      </label>
      <label>
        <input type="radio" :checked="mode === 'api'" @change="switchMode('api')" />
        REST API
      </label>
      <input v-if="mode === 'api'" v-model="apiUrl" class="url" />
    </section>
    <p v-if="error" class="error">{{ error }}</p>

    <form class="row" @submit.prevent="handleAdd">
      <input type="text" v-model="title" placeholder="New task..." />
      <button type="submit">Add</button>
    </form>

    <section class="row filters">
      <button
        v-for="f in FILTERS"
        :key="f"
        :class="{ active: filter === f }"
        @click="filter = f"
      >
        {{ f }}
      </button>
      <span class="stats">
        total {{ stats.total }} / active {{ stats.active }} / done {{ stats.done }}
      </span>
    </section>

    <ul class="tasks">
      <li v-for="t in visible" :key="t.id">
        <label>
          <input type="checkbox" :checked="t.done" @change="handleToggle(t)" />
          <span :class="{ done: t.done }">{{ t.title }}</span>
        </label>
        <button @click="handleRemove(t.id)">✕</button>
      </li>
    </ul>

    <section class="bench">
      <button @click="runBench(1_000)">Bench 1,000</button>
      <button @click="runBench(10_000)">Bench 10,000</button>
      <button @click="tasks = []">Clear</button>
      <p v-if="report">
        N={{ report.n.toLocaleString() }}: render {{ report.render.ms }}ms / update-all
        {{ report.update.ms }}ms
        <template v-if="report.update.fps !== null">({{ report.update.fps }} fps)</template>
      </p>
    </section>
  </main>
</template>
