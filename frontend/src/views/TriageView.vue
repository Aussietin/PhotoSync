<template>
  <div class="flex flex-col items-center max-w-xl mx-auto space-y-4">
    <!-- Header & Filter options -->
    <div class="w-full flex flex-wrap items-center justify-between gap-3 bg-ink-900/60 p-3 rounded-2xl border border-white/5 backdrop-blur-md">
      <h1 class="text-xl font-extrabold tracking-tight text-white flex items-center gap-2">
        <span>Triage Mode</span>
        <span v-if="queue.length" class="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-brand-500/20 text-brand-300 border border-brand-400/20">
          {{ currentIndex + 1 }}/{{ queue.length }}
        </span>
      </h1>

      <!-- Filter queue checkboxes -->
      <div class="flex items-center gap-2 text-xs flex-wrap">
        <label class="flex items-center gap-1.5 text-gray-300 cursor-pointer select-none">
          <input v-model="opts.screenshots" type="checkbox" class="accent-brand-500 rounded" @change="reload" />
          <span>Screenshots</span>
        </label>
        <label class="flex items-center gap-1.5 text-gray-300 cursor-pointer select-none">
          <input v-model="opts.duplicates" type="checkbox" class="accent-brand-500 rounded" @change="reload" />
          <span>Duplicates</span>
        </label>
        <label class="flex items-center gap-1.5 text-gray-300 cursor-pointer select-none">
          <input v-model="opts.low_quality" type="checkbox" class="accent-brand-500 rounded" @change="reload" />
          <span>Low Quality</span>
        </label>
      </div>
    </div>

    <!-- Progress bar -->
    <div v-if="queue.length && !done" class="w-full space-y-1.5 bg-ink-900/40 p-3 rounded-xl border border-white/5">
      <div class="flex justify-between text-xs font-medium">
        <span class="text-gray-400">Progress: <strong class="text-gray-200 font-mono">{{ Math.round(((currentIndex) / queue.length) * 100) }}%</strong></span>
        <div class="flex items-center gap-3 font-mono">
          <span class="text-red-400">🗑 {{ toDelete.size }} delete</span>
          <span class="text-emerald-400">✓ {{ toKeep.size }} keep</span>
        </div>
      </div>
      <ProgressBar :value="(currentIndex / queue.length) * 100" :height="6" />
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex flex-col items-center py-20 gap-4">
      <Spinner :size="36" label="Building triage queue…" />
    </div>

    <!-- Done state -->
    <div v-else-if="done || !queue.length" class="card p-8 flex flex-col items-center gap-5 text-center w-full border-brand-500/20 bg-ink-900/90 shadow-glow">
      <div class="w-16 h-16 rounded-2xl bg-brand-gradient flex items-center justify-center text-3xl shadow-glow">
        🎉
      </div>
      <div>
        <h2 class="text-xl font-bold text-gray-100">Triage Session Complete!</h2>
        <p class="text-gray-400 text-sm mt-1 max-w-sm">
          {{ toDelete.size > 0 ? `You marked ${toDelete.size} photo${toDelete.size !== 1 ? 's' : ''} for removal and kept ${toKeep.size}.` : 'You reviewed all photos in this queue with 0 marked for deletion.' }}
        </p>
      </div>

      <div v-if="toDelete.size" class="flex flex-wrap gap-3 justify-center pt-2">
        <button class="btn-ghost text-sm" @click="resetSession">Reset & Review Again</button>
        <button class="btn-danger text-sm px-5 py-2.5" @click="executeDeletes">
          🗑 Move {{ toDelete.size }} to Trash
        </button>
      </div>
      <button v-else class="btn-primary text-sm px-6" @click="reload">Reload Queue</button>
    </div>

    <!-- Triage active card -->
    <template v-else-if="current">
      <div
        class="w-full relative touch-none select-none"
        @touchstart="handleTouchStart"
        @touchmove="handleTouchMove"
        @touchend="handleTouchEnd"
      >
        <!-- Card Container with Swipe Drag Physics -->
        <div
          class="card overflow-hidden relative border-white/10 shadow-2xl transition-transform duration-100"
          :style="cardTransformStyle"
        >
          <!-- Reason badge overlay -->
          <div class="absolute top-3 left-3 z-20 flex items-center gap-2">
            <span
              class="px-3 py-1 rounded-full text-xs font-bold tracking-wide uppercase backdrop-blur-md shadow-md"
              :class="reasonClass"
            >
              {{ reasonLabel }}
            </span>
          </div>

          <!-- Photo Canvas -->
          <div class="w-full bg-black flex items-center justify-center min-h-[42vh] max-h-[55vh] relative">
            <img
              :src="current.original_url"
              :alt="current.filename"
              class="w-full max-h-[55vh] object-contain"
              draggable="false"
            />

            <!-- Drag indicator overlays -->
            <div
              v-if="dragOffset < -40 || decision === 'delete'"
              class="absolute inset-0 bg-red-600/40 backdrop-blur-xs flex items-center justify-center transition-opacity"
            >
              <div class="w-20 h-20 rounded-full bg-red-600/80 flex items-center justify-center text-4xl shadow-2xl animate-scale-in">
                🗑
              </div>
            </div>

            <div
              v-if="dragOffset > 40 || decision === 'keep'"
              class="absolute inset-0 bg-emerald-600/40 backdrop-blur-xs flex items-center justify-center transition-opacity"
            >
              <div class="w-20 h-20 rounded-full bg-emerald-600/80 flex items-center justify-center text-4xl shadow-2xl animate-scale-in">
                ✓
              </div>
            </div>
          </div>

          <!-- Metadata Strip -->
          <div class="p-3.5 bg-ink-850/90 border-t border-white/5 flex flex-wrap items-center justify-between gap-2 text-xs text-gray-400">
            <div class="truncate max-w-[65%] font-medium text-gray-300">{{ current.filename }}</div>
            <div class="flex items-center gap-2 flex-wrap font-mono">
              <span v-if="current.taken_at">📅 {{ formatDate(current.taken_at) }}</span>
              <span v-if="current.quality_score != null" :class="qualityColor" class="font-bold">
                ⭐ {{ Math.round(current.quality_score * 100) }}%
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="grid grid-cols-3 gap-3 w-full pt-1">
        <button
          class="flex flex-col items-center py-3.5 px-2 rounded-2xl bg-red-500/10 hover:bg-red-500/20 active:scale-95 text-red-400 border border-red-500/20 transition-all font-semibold gap-0.5 shadow-sm"
          title="Delete (D or Left Arrow)"
          @click="decide('delete')"
        >
          <span class="text-2xl">🗑</span>
          <span class="text-sm">Delete</span>
          <span class="text-[10px] text-red-400/60 font-mono">← or D</span>
        </button>

        <button
          class="flex flex-col items-center py-3.5 px-2 rounded-2xl bg-ink-850 hover:bg-ink-800 active:scale-95 text-gray-300 border border-white/5 transition-all font-semibold gap-0.5 shadow-sm"
          title="Skip (S)"
          @click="decide('skip')"
        >
          <span class="text-2xl">⏭</span>
          <span class="text-sm">Skip</span>
          <span class="text-[10px] text-gray-500 font-mono">S</span>
        </button>

        <button
          class="flex flex-col items-center py-3.5 px-2 rounded-2xl bg-emerald-500/10 hover:bg-emerald-500/20 active:scale-95 text-emerald-400 border border-emerald-500/20 transition-all font-semibold gap-0.5 shadow-sm"
          title="Keep (K or Right Arrow)"
          @click="decide('keep')"
        >
          <span class="text-2xl">✓</span>
          <span class="text-sm">Keep</span>
          <span class="text-[10px] text-emerald-400/60 font-mono">→ or K</span>
        </button>
      </div>

      <!-- Undo Bar -->
      <div class="flex items-center justify-between w-full px-1 text-xs text-gray-500">
        <span>Tip: Swipe left/right on mobile</span>
        <button
          v-if="history.length"
          class="text-brand-300 hover:text-brand-200 font-medium hover:underline flex items-center gap-1"
          @click="undo"
        >
          ↩ Undo previous (Ctrl+Z)
        </button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { photosApi } from '../api/photos'
import Spinner from '../components/ui/Spinner.vue'
import ProgressBar from '../components/ui/ProgressBar.vue'
import { useToast } from '../composables/useToast'

const { success } = useToast()

const queue = ref([])
const currentIndex = ref(0)
const toDelete = ref(new Set())
const toKeep = ref(new Set())
const history = ref([])
const loading = ref(false)
const done = ref(false)
const decision = ref(null)
const opts = ref({ screenshots: true, duplicates: true, low_quality: true })

// Touch drag state
const touchStartX = ref(0)
const dragOffset = ref(0)

const current = computed(() => queue.value[currentIndex.value] ?? null)

const reasonLabel = computed(() => ({
  screenshot: '📱 Screenshot',
  duplicate: '🔁 Duplicate',
  low_quality: '⚠️ Low Quality',
}[current.value?.triage_reason] ?? 'Review'))

const reasonClass = computed(() => ({
  screenshot: 'bg-purple-500/30 text-purple-200 border border-purple-400/30',
  duplicate: 'bg-amber-500/30 text-amber-200 border border-amber-400/30',
  low_quality: 'bg-rose-500/30 text-rose-200 border border-rose-400/30',
}[current.value?.triage_reason] ?? 'bg-ink-800 text-gray-300 border border-white/10'))

const qualityColor = computed(() => {
  const q = current.value?.quality_score
  if (q == null) return ''
  return q >= 0.7 ? 'text-emerald-400' : q >= 0.4 ? 'text-amber-400' : 'text-rose-400'
})

const cardTransformStyle = computed(() => {
  if (!dragOffset.value) return {}
  const deg = (dragOffset.value / 15).toFixed(1)
  return {
    transform: `translateX(${dragOffset.value}px) rotate(${deg}deg)`,
  }
})

function handleTouchStart(e) {
  if (e.touches.length === 1) {
    touchStartX.value = e.touches[0].clientX
  }
}

function handleTouchMove(e) {
  if (e.touches.length === 1) {
    const diff = e.touches[0].clientX - touchStartX.value
    dragOffset.value = diff
  }
}

function handleTouchEnd() {
  if (dragOffset.value < -80) {
    decide('delete')
  } else if (dragOffset.value > 80) {
    decide('keep')
  }
  dragOffset.value = 0
}

async function reload() {
  loading.value = true
  done.value = false
  currentIndex.value = 0
  toDelete.value = new Set()
  toKeep.value = new Set()
  history.value = []
  try {
    const { data } = await photosApi.triageQueue({
      include_screenshots: opts.value.screenshots,
      include_duplicates: opts.value.duplicates,
      include_low_quality: opts.value.low_quality,
    })
    queue.value = data.queue
  } finally {
    loading.value = false
  }
}

function decide(action) {
  if (!current.value) return
  const id = current.value.id
  decision.value = action
  history.value.push({ index: currentIndex.value, id, action })

  if (action === 'delete') toDelete.value = new Set([...toDelete.value, id])
  else if (action === 'keep') toKeep.value = new Set([...toKeep.value, id])

  setTimeout(() => {
    decision.value = null
    if (currentIndex.value >= queue.value.length - 1) {
      done.value = true
    } else {
      currentIndex.value++
    }
  }, 160)
}

function undo() {
  const last = history.value.pop()
  if (!last) return
  const next = new Set(toDelete.value); next.delete(last.id); toDelete.value = next
  const keep = new Set(toKeep.value); keep.delete(last.id); toKeep.value = keep
  currentIndex.value = last.index
  done.value = false
}

async function executeDeletes() {
  const ids = [...toDelete.value]
  if (!ids.length) return
  await photosApi.bulkDelete(ids)
  success(`Moved ${ids.length} photo${ids.length > 1 ? 's' : ''} to Trash`)
  toDelete.value = new Set()
  done.value = false
  await reload()
}

function resetSession() {
  toDelete.value = new Set()
  toKeep.value = new Set()
  history.value = []
  currentIndex.value = 0
  done.value = false
}

function handleKey(e) {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return
  if (e.key === 'ArrowRight' || e.key === 'k' || e.key === 'K') decide('keep')
  else if (e.key === 'ArrowLeft' || e.key === 'd' || e.key === 'D') decide('delete')
  else if (e.key === 's' || e.key === 'S') decide('skip')
  else if (e.key === 'z' && (e.ctrlKey || e.metaKey)) undo()
}

onMounted(() => {
  reload()
  window.addEventListener('keydown', handleKey)
})
onBeforeUnmount(() => window.removeEventListener('keydown', handleKey))

function formatDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}
</script>
