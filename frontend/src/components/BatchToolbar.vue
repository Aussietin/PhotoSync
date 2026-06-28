<template>
  <Transition name="slide-up">
    <div
      v-if="count > 0"
      class="fixed bottom-20 sm:bottom-6 inset-x-0 flex justify-center z-40 px-4 pointer-events-none"
    >
      <div class="pointer-events-auto bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl px-4 py-3 flex items-center gap-3 max-w-lg w-full">
        <span class="text-sm font-medium text-gray-300 flex-shrink-0">
          {{ count }} selected
        </span>

        <div class="flex-1 flex items-center gap-2 overflow-x-auto no-scrollbar">
          <button class="toolbar-btn" @click="$emit('favorite')">
            <span>♥</span> Favorite
          </button>
          <button class="toolbar-btn" @click="$emit('download')">
            <span>⬇</span> ZIP
          </button>
          <slot name="extra" />
          <button class="toolbar-btn text-red-400 hover:text-red-300" @click="$emit('delete')">
            <span>🗑</span> Delete
          </button>
        </div>

        <button
          class="flex-shrink-0 w-7 h-7 rounded-full bg-gray-800 hover:bg-gray-700 text-gray-400 flex items-center justify-center text-sm"
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
  @apply flex items-center gap-1 px-3 py-1.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm font-medium transition-colors whitespace-nowrap;
}
.slide-up-enter-active,
.slide-up-leave-active {
  transition: transform 0.2s ease, opacity 0.2s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  transform: translateY(20px);
  opacity: 0;
}
.no-scrollbar::-webkit-scrollbar { display: none; }
.no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
</style>
