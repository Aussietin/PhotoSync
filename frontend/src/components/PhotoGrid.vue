<template>
  <div>
    <div
      v-if="photos.length"
      class="grid gap-0.5"
      :style="{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }"
    >
      <PhotoCard
        v-for="photo in photos"
        :key="photo.id"
        :photo="photo"
        :selected="selection?.isSelected(photo.id) ?? false"
        :selection-mode="selectionMode"
        @click="$emit('select', photo)"
        @select="selection?.toggle(photo.id)"
        @toggle-favorite="$emit('toggle-favorite', $event)"
      />
    </div>
    <div v-else class="flex flex-col items-center justify-center py-24 text-gray-600">
      <span class="text-5xl mb-4">📷</span>
      <p class="text-lg">No photos here</p>
      <router-link v-if="showUploadHint" to="/upload" class="btn-primary mt-4 text-sm">Upload photos</router-link>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import PhotoCard from './PhotoCard.vue'

const props = defineProps({
  photos: { type: Array, default: () => [] },
  selection: { type: Object, default: null },
  selectionMode: { type: Boolean, default: false },
  showUploadHint: { type: Boolean, default: true },
})
defineEmits(['select', 'toggle-favorite'])

const cols = computed(() => {
  if (typeof window === 'undefined') return 3
  return window.innerWidth < 640 ? 3 : window.innerWidth < 1024 ? 4 : 6
})
</script>
