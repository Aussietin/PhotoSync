<template>
  <div
    class="w-full bg-ink-800/80 rounded-full overflow-hidden"
    :style="{ height: `${height}px` }"
  >
    <div
      class="h-full rounded-full bg-brand-gradient transition-all duration-500 ease-out relative overflow-hidden"
      :style="{ width: `${clamped}%` }"
    >
      <!-- animated stripe sheen while indeterminate / in flight -->
      <div
        v-if="active"
        class="absolute inset-0 opacity-40"
        style="
          background-image: linear-gradient(
            45deg,
            rgba(255, 255, 255, 0.25) 25%,
            transparent 25%,
            transparent 50%,
            rgba(255, 255, 255, 0.25) 50%,
            rgba(255, 255, 255, 0.25) 75%,
            transparent 75%
          );
          background-size: 40px 40px;
        "
        :class="active && 'animate-bar-stripe'"
      />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 },
  height: { type: Number, default: 8 },
  active: { type: Boolean, default: true },
})

const clamped = computed(() => Math.max(3, Math.min(100, props.value || 0)))
</script>
