<template>
  <Teleport to="body">
    <div class="fixed top-3 inset-x-0 z-[100] flex flex-col items-center gap-2 px-4 pointer-events-none">
      <TransitionGroup name="toast">
        <div
          v-for="t in toasts"
          :key="t.id"
          class="pointer-events-auto w-full max-w-sm glass shadow-soft px-4 py-3 flex items-center gap-3"
          :class="ring(t.type)"
        >
          <span class="text-lg leading-none flex-shrink-0">{{ icon(t.type) }}</span>
          <p class="text-sm text-gray-100 flex-1 leading-snug">{{ t.message }}</p>
          <button
            v-if="t.action"
            class="text-xs font-semibold text-brand-300 hover:text-brand-200 flex-shrink-0"
            @click="run(t)"
          >
            {{ t.action.label }}
          </button>
          <button
            class="flex-shrink-0 w-6 h-6 grid place-items-center rounded-full hover:bg-white/10 text-gray-400 text-sm"
            @click="dismiss(t.id)"
          >
            ✕
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup>
import { useToast } from '../../composables/useToast'

const { toasts, dismiss } = useToast()

const icon = (type) =>
  ({ success: '✅', error: '⚠️', info: '💡' }[type] || '💡')

const ring = (type) =>
  ({
    success: 'border-l-2 border-l-green-400/70',
    error: 'border-l-2 border-l-red-400/70',
    info: 'border-l-2 border-l-brand-400/70',
  }[type] || '')

function run(t) {
  t.action?.onClick?.()
  dismiss(t.id)
}
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}
.toast-enter-from {
  opacity: 0;
  transform: translateY(-16px) scale(0.95);
}
.toast-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.97);
}
.toast-move {
  transition: transform 0.3s ease;
}
</style>
