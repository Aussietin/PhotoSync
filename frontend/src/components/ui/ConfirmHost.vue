<template>
  <Teleport to="body">
    <Transition name="confirm">
      <div
        v-if="state"
        class="fixed inset-0 z-[90] flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
        @click.self="resolve(false)"
        @keydown.esc="resolve(false)"
      >
        <div class="glass shadow-soft w-full max-w-sm p-6 text-center animate-scale-in">
          <div
            class="w-14 h-14 mx-auto mb-4 rounded-2xl grid place-items-center text-2xl"
            :class="state.danger ? 'bg-red-500/15 border border-red-500/30' : 'bg-brand-500/15 border border-brand-400/30'"
          >
            {{ state.icon }}
          </div>
          <h2 class="text-lg font-semibold text-gray-100">{{ state.title }}</h2>
          <p v-if="state.message" class="text-sm text-gray-400 mt-2 leading-relaxed">{{ state.message }}</p>
          <div class="flex gap-2.5 mt-6">
            <button class="btn-ghost flex-1" @click="resolve(false)">{{ state.cancelText }}</button>
            <button
              class="flex-1"
              :class="state.danger ? 'btn-danger' : 'btn-primary'"
              @click="resolve(true)"
            >
              {{ state.confirmText }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { useConfirm } from '../../composables/useConfirm'

const { state, resolve } = useConfirm()
</script>

<style scoped>
.confirm-enter-active,
.confirm-leave-active {
  transition: opacity 0.2s ease;
}
.confirm-enter-from,
.confirm-leave-to {
  opacity: 0;
}
</style>
