<template>
  <router-link
    :to="to"
    class="relative flex flex-col items-center justify-center gap-0.5 text-[11px] font-medium transition-colors"
    :class="isActive ? 'text-brand-300' : 'text-gray-500 hover:text-gray-300'"
  >
    <span
      v-if="isActive"
      class="absolute -top-px h-1 w-8 rounded-full bg-brand-gradient"
    />
    <span
      class="text-xl leading-none transition-transform duration-150"
      :class="isActive ? 'scale-110' : ''"
    >{{ icon }}</span>
    <span>{{ label }}</span>
  </router-link>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { computed } from 'vue'

const props = defineProps({ to: String, icon: String, label: String })
const route = useRoute()
const isActive = computed(() =>
  props.to === '/' ? route.path === '/' : route.path.startsWith(props.to),
)
</script>
