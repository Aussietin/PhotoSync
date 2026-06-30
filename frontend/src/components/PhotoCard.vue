<template>
  <div
    class="relative aspect-square bg-gray-800 overflow-hidden cursor-pointer group"
    :class="selected && 'ring-2 ring-brand-500'"
    @click="handleClick"
    @long-press="$emit('long-press')"
  >
    <img
      v-if="photo.thumbnail_url"
      :src="photo.thumbnail_url"
      :alt="photo.filename"
      loading="lazy"
      class="w-full h-full object-cover transition-transform duration-200 group-hover:scale-105"
    />
    <div v-else class="flex items-center justify-center w-full h-full text-gray-600 text-3xl">
      {{ photo.is_video ? '🎬' : '🖼️' }}
    </div>

    <!-- Play overlay for videos -->
    <div
      v-if="photo.is_video"
      class="absolute inset-0 flex items-center justify-center pointer-events-none"
    >
      <span class="w-9 h-9 rounded-full bg-black/55 flex items-center justify-center text-white text-sm">▶</span>
    </div>

    <!-- Selection checkbox -->
    <div
      v-if="selectionMode || selected"
      class="absolute top-1.5 left-1.5 w-5 h-5 rounded-full border-2 flex items-center justify-center transition-colors"
      :class="selected ? 'bg-brand-500 border-brand-500' : 'bg-black/40 border-white/70'"
    >
      <svg v-if="selected" class="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
        <path d="M16.707 5.293a1 1 0 00-1.414 0L8 12.586 4.707 9.293a1 1 0 00-1.414 1.414l4 4a1 1 0 001.414 0l8-8a1 1 0 000-1.414z"/>
      </svg>
    </div>

    <!-- Favorite heart -->
    <button
      v-if="photo.is_favorite"
      class="absolute top-1.5 right-1.5 text-red-500 text-sm leading-none"
      @click.stop="$emit('toggle-favorite', photo.id)"
    >♥</button>

    <!-- Quality dot -->
    <div
      v-if="photo.quality_score != null"
      class="absolute bottom-1 right-1 w-2 h-2 rounded-full"
      :class="qualityColor"
      :title="`Quality: ${Math.round(photo.quality_score * 100)}%`"
    />

    <!-- Status badges -->
    <div class="absolute bottom-1 left-1 flex flex-col gap-0.5 items-start">
      <span v-if="photo.is_video" class="bg-sky-500 text-white text-xs font-bold px-1 rounded leading-tight">VID</span>
      <span v-if="photo.is_large" class="bg-pink-600 text-white text-xs font-bold px-1 rounded leading-tight">{{ sizeLabel }}</span>
      <span v-if="photo.is_screenshot" class="bg-purple-500 text-white text-xs font-bold px-1 rounded leading-tight">SS</span>
      <span v-if="photo.is_duplicate" class="bg-yellow-500 text-black text-xs font-bold px-1 rounded leading-tight">DUP</span>
      <span v-if="photo.is_meme" class="bg-orange-600 text-white text-xs font-bold px-1 rounded leading-tight">RCV</span>
    </div>

    <div class="absolute inset-0 bg-black/0 group-hover:bg-black/10 transition-colors" />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  photo: Object,
  selected: Boolean,
  selectionMode: Boolean,
})
const emit = defineEmits(['click', 'select', 'toggle-favorite', 'long-press'])

const qualityColor = computed(() => {
  const q = props.photo.quality_score
  if (q == null) return ''
  if (q >= 0.7) return 'bg-green-500'
  if (q >= 0.4) return 'bg-yellow-500'
  return 'bg-red-500'
})

const sizeLabel = computed(() => {
  const b = props.photo.file_size
  if (!b) return ''
  if (b >= 1073741824) return `${(b / 1073741824).toFixed(1)}GB`
  return `${Math.round(b / 1048576)}MB`
})

function handleClick() {
  if (props.selectionMode) emit('select', props.photo.id)
  else emit('click')
}
</script>
