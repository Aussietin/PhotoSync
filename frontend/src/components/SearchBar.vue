<template>
  <div class="relative">
    <span class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">🔍</span>
    <input
      :value="modelValue"
      type="search"
      :placeholder="placeholder"
      class="input pl-9"
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
