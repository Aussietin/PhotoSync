<template>
  <Teleport to="body">
    <Transition name="sheet-fade">
      <div
        v-if="open"
        class="sm:hidden fixed inset-0 z-[70] bg-black/60 backdrop-blur-sm"
        @click.self="$emit('close')"
      >
        <Transition name="sheet">
          <div
            v-if="open"
            class="absolute bottom-0 inset-x-0 glass !rounded-b-none rounded-t-3xl p-5 pb-8 max-h-[80vh] overflow-y-auto"
          >
            <div class="w-10 h-1 rounded-full bg-white/20 mx-auto mb-5" />
            <div v-for="group in groups" :key="group.title" class="mb-5 last:mb-0">
              <p class="text-[11px] font-semibold uppercase tracking-wider text-gray-500 mb-2 px-1">
                {{ group.title }}
              </p>
              <div class="grid grid-cols-2 gap-2">
                <router-link
                  v-for="item in group.items"
                  :key="item.to"
                  :to="item.to"
                  class="flex items-center gap-3 p-3 rounded-2xl bg-white/5 active:scale-[0.97] transition-transform"
                  @click="$emit('close')"
                >
                  <span class="text-xl">{{ item.icon }}</span>
                  <span class="text-sm font-medium text-gray-200">{{ item.label }}</span>
                </router-link>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { navGroups } from '../nav'

defineProps({ open: Boolean })
defineEmits(['close'])
const groups = navGroups
</script>

<style scoped>
.sheet-fade-enter-active,
.sheet-fade-leave-active {
  transition: opacity 0.25s ease;
}
.sheet-fade-enter-from,
.sheet-fade-leave-to {
  opacity: 0;
}
.sheet-enter-active,
.sheet-leave-active {
  transition: transform 0.3s cubic-bezier(0.22, 1, 0.36, 1);
}
.sheet-enter-from,
.sheet-leave-to {
  transform: translateY(100%);
}
</style>
