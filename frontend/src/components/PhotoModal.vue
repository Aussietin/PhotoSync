<template>
  <Teleport to="body">
    <div
      v-if="photo"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-md p-2 sm:p-4 transition-all"
      @click.self="$emit('close')"
    >
      <!-- Prev / Next arrows -->
      <button
        v-if="hasPrev"
        class="absolute left-2 sm:left-4 top-1/2 -translate-y-1/2 w-11 h-11 rounded-full bg-ink-900/80 hover:bg-ink-800 border border-white/10 text-white flex items-center justify-center text-2xl z-20 shadow-xl transition-all hover:scale-110 active:scale-95"
        title="Previous photo (←)"
        @click="$emit('prev')"
      >‹</button>
      <button
        v-if="hasNext"
        class="absolute right-2 sm:right-4 top-1/2 -translate-y-1/2 w-11 h-11 rounded-full bg-ink-900/80 hover:bg-ink-800 border border-white/10 text-white flex items-center justify-center text-2xl z-20 shadow-xl transition-all hover:scale-110 active:scale-95"
        title="Next photo (→)"
        @click="$emit('next')"
      >›</button>

      <div class="card max-w-3xl w-full max-h-[92vh] overflow-hidden flex flex-col animate-scale-in border-white/10 shadow-2xl">
        <!-- Media View Area -->
        <div class="relative bg-black flex-1 min-h-[40vh] max-h-[62vh] flex items-center justify-center overflow-hidden select-none">
          <video
            v-if="photo.is_video"
            :src="photo.original_url"
            controls
            autoplay
            playsinline
            class="max-w-full max-h-[62vh] object-contain"
          />
          <img
            v-else
            :src="photo.preview_url || photo.original_url"
            :alt="photo.filename"
            class="max-w-full max-h-[62vh] object-contain transition-transform duration-200 cursor-zoom-in"
            :class="zoomed && 'scale-150 cursor-zoom-out'"
            @click="zoomed = !zoomed"
          />

          <!-- Top-left controls: Favorite + Badges -->
          <div class="absolute top-3 left-3 flex items-center gap-2 z-10">
            <button
              class="w-9 h-9 rounded-full bg-black/60 backdrop-blur-md flex items-center justify-center text-lg leading-none transition-transform hover:scale-110 shadow-md border border-white/10"
              :class="photo.is_favorite ? 'text-red-500 bg-black/80' : 'text-white/70 hover:text-red-400'"
              :title="photo.is_favorite ? 'Unfavorite' : 'Favorite (F)'"
              @click="$emit('toggle-favorite', photo.id)"
            >
              ♥
            </button>
            <div class="flex items-center gap-1">
              <span v-if="photo.is_video" class="badge-video">VID</span>
              <span v-if="photo.is_large" class="badge-size">{{ sizeLabel }}</span>
              <span v-if="photo.is_screenshot" class="badge-screenshot">SS</span>
              <span v-if="photo.is_duplicate" class="badge-duplicate">DUP</span>
              <span v-if="photo.is_meme" class="badge-meme">RCV</span>
            </div>
          </div>

          <!-- Top-right: Close button -->
          <button
            class="absolute top-3 right-3 w-9 h-9 flex items-center justify-center rounded-full bg-black/60 backdrop-blur-md text-white/80 hover:text-white hover:bg-black/80 border border-white/10 shadow-md transition-all hover:scale-110 z-10 text-sm"
            title="Close (Esc)"
            @click="$emit('close')"
          >✕</button>
        </div>

        <!-- Metadata & Controls Area -->
        <div class="p-4 sm:p-5 bg-ink-900 border-t border-white/5 space-y-3 overflow-y-auto max-h-[35vh]">
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <h2 class="font-bold text-sm text-gray-200 truncate select-all">{{ photo.filename }}</h2>
              <p class="text-xs text-gray-500 mt-0.5">{{ formatBytes(photo.file_size) }} • {{ photo.width }}×{{ photo.height }}</p>
            </div>
            <button
              class="btn-ghost text-xs py-1 px-2.5 flex-shrink-0"
              @click="showExif = !showExif"
            >
              {{ showExif ? 'Hide EXIF ▴' : 'Show EXIF ▾' }}
            </button>
          </div>

          <!-- Collapsible EXIF Grid -->
          <Transition name="fade">
            <div v-if="showExif" class="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs bg-ink-850/80 p-3 rounded-xl border border-white/5">
              <div v-if="photo.taken_at"><span class="text-gray-500">Taken</span><br/><span class="text-gray-300 font-medium">{{ formatDate(photo.taken_at) }}</span></div>
              <div v-if="photo.camera"><span class="text-gray-500">Camera</span><br/><span class="text-gray-300 font-medium">{{ photo.camera }}</span></div>
              <div v-if="photo.quality_score != null">
                <span class="text-gray-500">Quality Score</span><br/>
                <span :class="qualityColor" class="font-semibold">{{ Math.round(photo.quality_score * 100) }}%</span>
              </div>
              <div v-if="photo.gps">
                <span class="text-gray-500">GPS Coordinates</span><br/>
                <span class="text-gray-300 font-mono">{{ photo.gps.lat.toFixed(4) }}, {{ photo.gps.lon.toFixed(4) }}</span>
              </div>
              <div v-if="photo.created_at">
                <span class="text-gray-500">Imported</span><br/>
                <span class="text-gray-300">{{ formatDate(photo.created_at) }}</span>
              </div>
              <div v-if="photo.file_path" class="col-span-2 sm:col-span-3">
                <span class="text-gray-500">File Path</span><br/>
                <span class="text-gray-400 font-mono text-[11px] break-all select-all">{{ photo.file_path }}</span>
              </div>
            </div>
          </Transition>

          <!-- Tags -->
          <div v-if="allTags.length" class="flex flex-wrap gap-1.5 items-center">
            <span class="text-xs text-gray-500 mr-1">Tags:</span>
            <span
              v-for="tag in allTags"
              :key="tag"
              class="px-2.5 py-0.5 bg-brand-500/15 border border-brand-400/25 rounded-full text-xs text-brand-200 font-medium"
            >{{ tag }}</span>
          </div>

          <!-- Notes / Caption -->
          <div>
            <textarea
              :value="photo.notes || ''"
              rows="2"
              placeholder="Add notes or a caption to this photo…"
              class="input resize-none text-xs"
              @change="$emit('update-notes', photo.id, $event.target.value)"
            />
          </div>

          <!-- Action bar -->
          <div class="flex items-center gap-2 pt-1 flex-wrap">
            <a :href="photo.original_url" download class="btn-ghost text-xs py-1.5 px-3">⬇ Download original</a>
            <button class="btn-ghost text-xs py-1.5 px-3" @click="$emit('toggle-favorite', photo.id)">
              {{ photo.is_favorite ? '♥ Favorited' : '♡ Add Favorite' }}
            </button>
            <button
              class="btn-danger text-xs py-1.5 px-3 ml-auto"
              @click="$emit('delete', photo.id)"
            >
              🗑 Move to Trash
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  photo: Object,
  hasPrev: Boolean,
  hasNext: Boolean,
})
const emit = defineEmits(['close', 'delete', 'toggle-favorite', 'update-notes', 'prev', 'next'])

const zoomed = ref(false)
const showExif = ref(false)

const allTags = computed(() => {
  if (!props.photo) return []
  const manual = props.photo.tags?.map((t) => t.name) ?? []
  const ai = props.photo.ai_tags ?? []
  return [...new Set([...manual, ...ai])]
})

const sizeLabel = computed(() => {
  const b = props.photo?.file_size
  if (!b) return ''
  if (b >= 1073741824) return `${(b / 1073741824).toFixed(1)}GB`
  return `${Math.round(b / 1048576)}MB`
})

const qualityColor = computed(() => {
  const q = props.photo?.quality_score
  if (q == null) return ''
  if (q >= 0.7) return 'text-emerald-400'
  if (q >= 0.4) return 'text-amber-400'
  return 'text-red-400'
})

function formatDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

function formatBytes(b) {
  if (!b) return '0 B'
  if (b < 1024) return `${b} B`
  if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`
  if (b < 1073741824) return `${(b / 1048576).toFixed(1)} MB`
  return `${(b / 1073741824).toFixed(2)} GB`
}

function handleKey(e) {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
  if (e.key === 'Escape') emit('close')
  else if (e.key === 'ArrowLeft' && props.hasPrev) emit('prev')
  else if (e.key === 'ArrowRight' && props.hasNext) emit('next')
  else if (e.key === 'f' || e.key === 'F') emit('toggle-favorite', props.photo?.id)
  else if (e.key === 'Delete') emit('delete', props.photo?.id)
}

onMounted(() => {
  window.addEventListener('keydown', handleKey)
})
onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKey)
})
</script>
