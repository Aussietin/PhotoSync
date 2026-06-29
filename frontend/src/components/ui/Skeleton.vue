<template>
  <div class="skeleton" :class="rounded" :style="style" />
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  width: { type: String, default: '100%' },
  height: { type: String, default: '1rem' },
  rounded: { type: String, default: 'rounded-lg' },
})

const style = computed(() => ({ width: props.width, height: props.height }))
</script>
