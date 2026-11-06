<script setup>
defineProps({
  name: { type: String, default: "arrow" },
  size: { type: [Number, String], default: 18 },
});
const paths = {
  arrow: "M4 12h16m-6-6 6 6-6 6",
  search: "m20 20-5-5M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0",
  graph: "M6 6l12 3M6 6l4 13m8-10-8 10",
  flow: "M3 6h5c5 0 3 12 8 12h5M3 18h5c5 0 3-12 8-12h5m-4-3 4 3-4 3m0 6 4 3-4 3",
  star: "m12 3 2.6 5.6 6.2.8-4.6 4.3 1.2 6.2-5.4-3-5.4 3 1.2-6.2L3.2 9.4l6.2-.8L12 3Z",
  expand: "M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5",
  download: "M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5",
  reset: "M4 10a8 8 0 1 1 1 7M4 4v6h6",
  plus: "M12 5v14M5 12h14",
  minus: "M5 12h14",
  close: "m6 6 12 12M6 18 18 6",
  check: "m5 12 4 4L19 6",
  info: "M12 11v6m0-10v.01M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0",
  menu: "M4 7h16M4 12h16M4 17h16",
  play: "m8 4 12 8-12 8V4Z",
  pause: "M8 4v16M16 4v16",
};
</script>
<template>
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.5"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <template v-if="name === 'graph'">
      <path :d="paths.graph" />
      <circle cx="6" cy="6" r="3" />
      <circle cx="18" cy="9" r="3" />
      <circle cx="10" cy="19" r="3" />
    </template>
    <path v-else :d="paths[name] || paths.arrow" />
  </svg>
</template>
