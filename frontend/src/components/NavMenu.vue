<template>
  <div ref="root" class="relative">
    <button
      class="group px-3 py-1.5 rounded-xl text-sm font-medium flex items-center gap-1.5 transition-all"
      :class="open || hasActiveChild
        ? 'text-white bg-white/10'
        : 'text-gray-400 hover:text-white hover:bg-white/5'"
      @click="open = !open"
    >
      <span>More</span>
      <svg
        class="w-3.5 h-3.5 transition-transform duration-200"
        :class="open && 'rotate-180'"
        viewBox="0 0 20 20" fill="currentColor"
      >
        <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.17l3.71-3.94a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd" />
      </svg>
    </button>

    <Transition name="menu">
      <div
        v-if="open"
        class="absolute right-0 mt-2 w-[30rem] glass shadow-soft p-3 grid grid-cols-3 gap-x-3 gap-y-1 z-50 origin-top-right"
      >
        <div v-for="group in groups" :key="group.title">
          <p class="px-2 pt-1 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-gray-500">
            {{ group.title }}
          </p>
          <router-link
            v-for="item in group.items"
            :key="item.to"
            :to="item.to"
            class="flex items-start gap-2.5 px-2 py-2 rounded-xl transition-colors hover:bg-white/5"
            :class="route.path.startsWith(item.to) && item.to !== '/' ? 'bg-white/5' : ''"
            @click="open = false"
          >
            <span class="text-lg leading-none mt-0.5">{{ item.icon }}</span>
            <span class="min-w-0">
              <span class="block text-sm font-medium text-gray-200 truncate">{{ item.label }}</span>
              <span class="block text-xs text-gray-500 truncate">{{ item.desc }}</span>
            </span>
          </router-link>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { navGroups } from '../nav'

const route = useRoute()
const groups = navGroups
const open = ref(false)
const root = ref(null)

const hasActiveChild = computed(() =>
  navGroups.some((g) => g.items.some((i) => route.path.startsWith(i.to) && i.to !== '/')),
)

function onDocClick(e) {
  if (root.value && !root.value.contains(e.target)) open.value = false
}
onMounted(() => document.addEventListener('click', onDocClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocClick))
</script>

<style scoped>
.menu-enter-active,
.menu-leave-active {
  transition: opacity 0.16s ease, transform 0.16s ease;
}
.menu-enter-from,
.menu-leave-to {
  opacity: 0;
  transform: translateY(-6px) scale(0.97);
}
</style>
