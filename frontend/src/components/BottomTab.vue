<template>
  <router-link
    :to="to"
    class="flex flex-col items-center justify-center gap-0.5 text-xs transition-colors"
    :class="[
      isActive ? 'text-brand-500' : 'text-gray-500',
      primary ? 'scale-110' : '',
    ]"
  >
    <span class="text-xl leading-none">{{ icon }}</span>
    <span>{{ label }}</span>
  </router-link>
</template>

<script setup>
import { useRoute } from 'vue-router'
import { computed } from 'vue'

const props = defineProps({ to: String, icon: String, label: String, primary: Boolean })
const route = useRoute()
const isActive = computed(() => route.path === props.to)
</script>
