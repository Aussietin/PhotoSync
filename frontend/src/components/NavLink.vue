<template>
  <router-link
    :to="to"
    class="group relative px-3 py-1.5 rounded-xl text-sm font-medium transition-all duration-150 flex items-center gap-1.5 whitespace-nowrap"
    :class="isActive
      ? 'text-white bg-white/10 shadow-soft'
      : 'text-gray-400 hover:text-white hover:bg-white/5'"
  >
    <span v-if="icon" class="text-base leading-none transition-transform duration-150 group-hover:scale-110">{{ icon }}</span>
    <span><slot /></span>
    <span
      v-if="isActive"
      class="absolute -bottom-px left-1/2 -translate-x-1/2 h-0.5 w-5 rounded-full bg-brand-gradient"
    />
  </router-link>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { computed } from 'vue'

const props = defineProps({ to: String, icon: { type: String, default: '' } })
const route = useRoute()
const isActive = computed(() =>
  props.to === '/' ? route.path === '/' : route.path.startsWith(props.to),
)
</script>
