<template>
  <Teleport to="body">
    <div
      v-if="photo"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
      @click.self="$emit('close')"
    >
      <!-- Prev / Next arrows -->
      <button
        v-if="hasPrev"
        class="absolute left-3 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/60 hover:bg-black/80 text-white flex items-center justify-center text-xl z-10"
        @click="$emit('prev')"
      >‹</button>
      <button
        v-if="hasNext"
        class="absolute right-3 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-black/60 hover:bg-black/80 text-white flex items-center justify-center text-xl z-10"
        @click="$emit('next')"
      >›</button>

      <div class="card max-w-2xl w-full max-h-[90vh] overflow-y-auto animate-scale-in">
        <!-- Image -->
        <div class="relative bg-black flex items-center justify-center" style="max-height:60vh">
          <img
            :src="photo.preview_url || photo.original_url"
            :alt="photo.filename"
            class="max-w-full max-h-[60vh] object-contain"
          />
          <button
            class="absolute top-3 right-3 w-8 h-8 flex items-center justify-center rounded-full bg-black/60 text-white hover:bg-black/80"
            @click="$emit('close')"
          >✕</button>
          <button
            class="absolute top-3 left-3 w-8 h-8 flex items-center justify-center rounded-full bg-black/40 text-xl leading-none transition-transform"
            :class="photo.is_favorite ? 'text-red-500' : 'text-white/60 hover:text-red-400'"
            @click="$emit('toggle-favorite', photo.id)"
          >♥</button>
        </div>

        <!-- Metadata -->
        <div class="p-4 space-y-3">
          <h2 class="font-semibold text-sm text-gray-300 truncate">{{ photo.filename }}</h2>

          <div class="grid grid-cols-2 gap-2 text-xs text-gray-400">
            <div v-if="photo.taken_at"><span class="text-gray-500">Taken</span><br/>{{ formatDate(photo.taken_at) }}</div>
            <div v-if="photo.camera"><span class="text-gray-500">Camera</span><br/>{{ photo.camera }}</div>
            <div v-if="photo.width"><span class="text-gray-500">Dimensions</span><br/>{{ photo.width }}×{{ photo.height }}</div>
            <div><span class="text-gray-500">File size</span><br/>{{ formatBytes(photo.file_size) }}</div>
            <div v-if="photo.quality_score != null">
              <span class="text-gray-500">Quality</span><br/>
              <span :class="qualityColor">{{ Math.round(photo.quality_score * 100) }}%</span>
            </div>
            <div v-if="photo.gps">
              <span class="text-gray-500">GPS</span><br/>
              {{ photo.gps.lat.toFixed(4) }}, {{ photo.gps.lon.toFixed(4) }}
            </div>
          </div>

          <!-- Tags -->
          <div v-if="allTags.length" class="flex flex-wrap gap-1">
            <span
              v-for="tag in allTags"
              :key="tag"
              class="px-2.5 py-0.5 bg-brand-500/15 border border-brand-400/20 rounded-full text-xs text-brand-200"
            >{{ tag }}</span>
          </div>

          <!-- Notes -->
          <div>
            <textarea
              :value="photo.notes || ''"
              rows="2"
              placeholder="Add a caption…"
              class="input resize-none"
              @change="$emit('update-notes', photo.id, $event.target.value)"
            />
          </div>

          <!-- Actions -->
          <div class="flex gap-2 pt-1 flex-wrap">
            <a :href="photo.original_url" download class="btn-ghost text-sm">⬇ Download</a>
            <button class="btn-ghost text-sm" @click="$emit('toggle-favorite', photo.id)">
              {{ photo.is_favorite ? '♥ Unfavorite' : '♡ Favorite' }}
            </button>
            <button class="btn-ghost text-sm text-red-400 hover:text-red-300 ml-auto" @click="$emit('delete', photo.id)">🗑 Delete</button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  photo: Object,
  hasPrev: Boolean,
  hasNext: Boolean,
})
defineEmits(['close', 'delete', 'toggle-favorite', 'update-notes', 'prev', 'next'])

const allTags = computed(() => {
  if (!props.photo) return []
  const manual = props.photo.tags?.map((t) => t.name) ?? []
  const ai = props.photo.ai_tags ?? []
  return [...new Set([...manual, ...ai])]
})

const qualityColor = computed(() => {
  const q = props.photo?.quality_score
  if (q == null) return ''
  if (q >= 0.7) return 'text-green-400'
  if (q >= 0.4) return 'text-yellow-400'
  return 'text-red-400'
})

function formatDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
}

function formatBytes(b) {
  if (b < 1024) return `${b} B`
  if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1048576).toFixed(1)} MB`
}
</script>
