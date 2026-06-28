<template>
  <div
    class="relative aspect-square bg-gray-800 overflow-hidden cursor-pointer group"
    @click="$emit('click')"
  >
    <img
      v-if="photo.thumbnail_url"
      :src="photo.thumbnail_url"
      :alt="photo.filename"
      loading="lazy"
      class="w-full h-full object-cover transition-transform duration-200 group-hover:scale-105"
    />
    <div v-else class="flex items-center justify-center w-full h-full text-gray-600 text-3xl">
      🖼️
    </div>

    <!-- Duplicate badge -->
    <span
      v-if="photo.is_duplicate"
      class="absolute top-1 right-1 bg-yellow-500 text-black text-xs font-bold px-1 rounded"
    >DUP</span>

    <!-- Hover overlay -->
    <div class="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors" />
  </div>
</template>

<script setup>
defineProps({ photo: Object })
defineEmits(['click'])
</script>
