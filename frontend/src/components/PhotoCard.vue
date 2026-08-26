<template>
  <div
    class="relative aspect-square bg-ink-900 rounded-xl overflow-hidden cursor-pointer group select-none transition-all duration-200 border border-white/5"
    :class="selected ? 'ring-2 ring-brand-400 ring-offset-2 ring-offset-ink-950 scale-[0.98]' : 'hover:border-white/20 hover:shadow-lg'"
    @click="handleClick"
    @long-press="$emit('long-press')"
  >
    <img
      v-if="photo.thumbnail_url"
      :src="photo.thumbnail_url"
      :alt="photo.filename"
      loading="lazy"
      class="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
    />
    <div v-else class="flex flex-col items-center justify-center w-full h-full text-gray-600 bg-ink-850">
      <span class="text-3xl mb-1">{{ photo.is_video ? '🎬' : '🖼️' }}</span>
      <span class="text-[10px] text-gray-500 font-mono truncate max-w-[80%]">{{ photo.filename }}</span>
    </div>

    <!-- Play overlay for videos -->
    <div
      v-if="photo.is_video"
      class="absolute inset-0 flex items-center justify-center pointer-events-none"
    >
      <span class="w-10 h-10 rounded-full bg-black/60 backdrop-blur-md flex items-center justify-center text-white text-sm shadow-lg group-hover:scale-110 transition-transform">
        ▶
      </span>
    </div>

    <!-- Selection checkbox -->
    <div
      v-if="selectionMode || selected"
      class="absolute top-2 left-2 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all duration-150 shadow-md"
      :class="selected ? 'bg-brand-500 border-brand-400 scale-105' : 'bg-black/50 border-white/70 backdrop-blur-sm group-hover:border-white'"
    >
      <svg v-if="selected" class="w-3.5 h-3.5 text-white" fill="currentColor" viewBox="0 0 20 20">
        <path d="M16.707 5.293a1 1 0 00-1.414 0L8 12.586 4.707 9.293a1 1 0 00-1.414 1.414l4 4a1 1 0 001.414 0l8-8a1 1 0 000-1.414z"/>
      </svg>
    </div>

    <!-- Favorite toggle button -->
    <button
      class="absolute top-2 right-2 w-7 h-7 rounded-full bg-black/50 backdrop-blur-md flex items-center justify-center transition-all duration-150 hover:scale-110 shadow-sm"
      :class="photo.is_favorite ? 'text-red-500 bg-black/70' : 'text-white/60 hover:text-red-400'"
      :title="photo.is_favorite ? 'Unfavorite' : 'Favorite — protects from all bulk cleanup'"
      @click.stop="$emit('toggle-favorite', photo.id)"
    >
      <span class="text-sm leading-none transition-transform" :class="photo.is_favorite && 'scale-110'">♥</span>
    </button>

    <!-- Quality dot indicator -->
    <div
      v-if="photo.quality_score != null"
      class="absolute bottom-2 right-2 w-2.5 h-2.5 rounded-full border border-black/40 shadow-sm"
      :class="qualityColor"
      :title="`Quality: ${Math.round(photo.quality_score * 100)}%`"
    />

    <!-- Status badges -->
    <div class="absolute bottom-2 left-2 flex flex-wrap gap-1 items-center max-w-[80%] pointer-events-none">
      <span v-if="photo.is_video" class="badge-video">VID</span>
      <span v-if="photo.is_large" class="badge-size">{{ sizeLabel }}</span>
      <span v-if="photo.is_screenshot" class="badge-screenshot">SS</span>
      <span v-if="photo.is_duplicate" class="badge-duplicate">DUP</span>
      <span v-if="photo.is_meme" class="badge-meme">RCV</span>
    </div>

    <!-- Hover tint -->
    <div class="absolute inset-0 bg-black/0 group-hover:bg-white/[0.03] transition-colors pointer-events-none" />
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
  if (q >= 0.7) return 'bg-emerald-400'
  if (q >= 0.4) return 'bg-amber-400'
  return 'bg-red-400'
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
