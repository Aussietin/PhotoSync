<template>
  <div class="flex flex-col items-center justify-center text-center px-6 py-20 animate-fade-up">
    <div class="relative mb-5">
      <div class="absolute inset-0 rounded-full bg-brand-gradient-soft blur-2xl opacity-70" />
      <div
        class="relative w-20 h-20 rounded-3xl grid place-items-center text-4xl bg-ink-850/80 border border-white/10 shadow-soft animate-float"
      >
        {{ icon }}
      </div>
    </div>
    <h3 class="text-lg font-semibold text-gray-100">{{ title }}</h3>
    <p v-if="subtitle" class="text-sm text-gray-500 mt-1.5 max-w-sm">{{ subtitle }}</p>
    <div v-if="$slots.action" class="mt-6">
      <slot name="action" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  icon: { type: String, default: '📷' },
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
})
</script>
