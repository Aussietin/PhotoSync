<template>
  <router-link
    :to="to"
    class="px-3 py-1.5 rounded-lg text-sm font-medium transition-colors"
    :class="isActive ? 'bg-gray-800 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800/50'"
  >
    <slot />
  </router-link>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { computed } from 'vue'

const props = defineProps({ to: String })
const route = useRoute()
const isActive = computed(() => route.path === props.to)
</script>
