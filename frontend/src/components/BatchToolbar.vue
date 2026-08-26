<template>
  <Transition name="slide-up">
    <div
      v-if="count > 0"
      class="fixed bottom-20 sm:bottom-6 inset-x-0 flex justify-center z-40 px-4 pointer-events-none"
    >
      <div class="pointer-events-auto glass shadow-glow px-4 py-3 flex items-center gap-3 max-w-xl w-full border border-brand-500/20 bg-ink-900/90 backdrop-blur-2xl rounded-2xl">
        <span class="text-sm font-bold text-gray-100 flex-shrink-0 flex items-center gap-2">
          <span class="grid place-items-center min-w-6 h-6 px-2 rounded-full bg-brand-gradient text-white text-xs font-mono shadow-sm">{{ count }}</span>
          <span class="hidden sm:inline">selected</span>
        </span>

        <div class="flex-1 flex items-center gap-2 overflow-x-auto no-scrollbar">
          <button class="toolbar-btn text-rose-300 hover:text-rose-200 hover:bg-rose-500/15" @click="$emit('favorite')">
            <span class="text-rose-400">♥</span>
            <span>Favorite</span>
          </button>
          <button class="toolbar-btn text-sky-300 hover:text-sky-200 hover:bg-sky-500/15" @click="$emit('download')">
            <span>⬇</span>
            <span>Download ZIP</span>
          </button>
          <slot name="extra" />
          <button class="toolbar-btn text-red-400 hover:text-red-300 hover:bg-red-500/20 ml-auto" @click="$emit('delete')">
            <span>🗑</span>
            <span>Trash</span>
          </button>
        </div>

        <button
          class="flex-shrink-0 w-8 h-8 rounded-full bg-white/5 hover:bg-white/15 text-gray-400 hover:text-white flex items-center justify-center text-xs transition-colors"
          title="Deselect all (Esc)"
          @click="$emit('clear')"
        >✕</button>
      </div>
    </div>
  </Transition>
</template>

<script setup>
defineProps({ count: { type: Number, default: 0 } })
defineEmits(['favorite', 'download', 'delete', 'clear'])
</script>

<style scoped>
.toolbar-btn {
  @apply flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 text-gray-200 text-xs font-semibold transition-all whitespace-nowrap active:scale-95 border border-white/5;
}
.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.22s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.22s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(24px) scale(0.96);
  opacity: 0;
}
.no-scrollbar::-webkit-scrollbar { display: none; }
.no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
</style>
