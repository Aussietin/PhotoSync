<template>
  <div class="relative">
    <span class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">🔍</span>
    <input
      :value="modelValue"
      type="search"
      :placeholder="placeholder"
      class="w-full bg-gray-800 border border-gray-700 rounded-xl pl-9 pr-4 py-2.5 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-brand-500 transition-colors"
      @input="$emit('update:modelValue', $event.target.value)"
      @keydown.enter="$emit('search')"
    />
  </div>
</template>

<script setup>
defineProps({
  modelValue: String,
  placeholder: { type: String, default: 'Search photos…' },
})
defineEmits(['update:modelValue', 'search'])
</script>
