<template>
  <span class="inline-flex items-center gap-2.5" role="status" :aria-label="label || 'Loading'">
    <span class="relative inline-flex" :style="{ width: px, height: px }">
      <svg class="animate-spin text-brand-400" :width="px" :height="px" viewBox="0 0 24 24" fill="none">
        <circle class="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" />
        <path
          d="M22 12a10 10 0 0 0-10-10"
          stroke="url(#spinner-grad)"
          stroke-width="3"
          stroke-linecap="round"
        />
        <defs>
          <linearGradient id="spinner-grad" x1="2" y1="2" x2="22" y2="22" gradientUnits="userSpaceOnUse">
            <stop stop-color="#60a5fa" />
            <stop offset="1" stop-color="#c084fc" />
          </linearGradient>
        </defs>
      </svg>
    </span>
    <span v-if="label" class="text-sm text-gray-400">{{ label }}</span>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  size: { type: Number, default: 24 },
  label: { type: String, default: '' },
})

const px = computed(() => `${props.size}px`)
</script>
