<script setup>
import { defineAsyncComponent, ref } from "vue";
import NetworkFallback from "./NetworkFallback.vue";
defineOptions({ inheritAttrs: false });
const fallback = ref(false);
const SpatialNetwork = defineAsyncComponent({
  loader: () => import("./SpatialNetwork.vue"),
  loadingComponent: NetworkFallback,
  delay: 100,
});
</script>
<template>
  <NetworkFallback v-if="fallback" v-bind="$attrs" />
  <SpatialNetwork v-else v-bind="$attrs" @unsupported="fallback = true" />
</template>
