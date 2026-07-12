<script setup lang="ts">
// Tiny hash "router": #board shows the live board, anything else the tasks app.
import { onUnmounted, ref } from 'vue';
import App from './App.vue';
import Board from './Board.vue';

const hash = ref(location.hash);
const onChange = () => (hash.value = location.hash);
addEventListener('hashchange', onChange);
onUnmounted(() => removeEventListener('hashchange', onChange));
</script>

<template>
  <Board v-if="hash === '#board'" />
  <App v-else />
</template>
