<template>
  <div
    class="grid gap-0.5"
    :style="{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }"
  >
    <div
      v-for="i in count"
      :key="i"
      class="skeleton aspect-square !rounded-none"
      :style="{ animationDelay: `${(i % cols) * 90}ms` }"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  count: { type: Number, default: 18 },
})

const cols = computed(() => {
  if (typeof window === 'undefined') return 3
  return window.innerWidth < 640 ? 3 : window.innerWidth < 1024 ? 4 : 6
})
</script>
