<template>
  <div class="flex flex-col items-center max-w-xl mx-auto">
    <div class="w-full flex items-center justify-between mb-4">
      <h1 class="text-2xl font-bold tracking-tight">Triage</h1>
      <div class="flex gap-2 text-sm">
        <label class="flex items-center gap-1.5 text-gray-400 cursor-pointer">
          <input v-model="opts.screenshots" type="checkbox" class="accent-brand-500" @change="reload" />
          Screenshots
        </label>
        <label class="flex items-center gap-1.5 text-gray-400 cursor-pointer">
          <input v-model="opts.duplicates" type="checkbox" class="accent-brand-500" @change="reload" />
          Duplicates
        </label>
        <label class="flex items-center gap-1.5 text-gray-400 cursor-pointer">
          <input v-model="opts.low_quality" type="checkbox" class="accent-brand-500" @change="reload" />
          Low quality
        </label>
      </div>
    </div>

    <!-- Progress bar -->
    <div v-if="queue.length" class="w-full mb-4">
      <div class="flex justify-between text-xs text-gray-500 mb-1">
        <span>{{ currentIndex + 1 }} of {{ queue.length }}</span>
        <span>🗑 {{ toDelete.size }} to delete &nbsp; ✓ {{ toKeep.size }} kept</span>
      </div>
      <ProgressBar :value="(currentIndex / queue.length) * 100" :height="6" :active="false" />
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex flex-col items-center py-20 gap-4">
      <Spinner :size="34" />
      <span class="text-gray-500 text-sm">Building triage queue…</span>
    </div>

    <!-- Done state -->
    <div v-else-if="done || !queue.length" class="flex flex-col items-center py-16 gap-4 text-center w-full">
      <span class="text-6xl">🎉</span>
      <h2 class="text-lg font-semibold">Triage complete!</h2>
      <p class="text-gray-400 text-sm">
        {{ toDelete.size > 0 ? `${toDelete.size} photo${toDelete.size !== 1 ? 's' : ''} queued for deletion.` : 'Nothing to delete.' }}
      </p>
      <div v-if="toDelete.size" class="flex gap-3">
        <button class="btn-ghost" @click="resetSession">Cancel</button>
        <button class="btn-primary" @click="executeDeletes">
          🗑 Send {{ toDelete.size }} to trash
        </button>
      </div>
      <button v-else class="btn-primary" @click="reload">Reload queue</button>
    </div>

    <!-- Triage card -->
    <template v-else-if="current">
      <!-- Reason badge -->
      <div class="mb-3">
        <span
          class="px-3 py-1 rounded-full text-sm font-medium"
          :class="reasonClass"
        >{{ reasonLabel }}</span>
      </div>

      <!-- Photo -->
      <div class="w-full card overflow-hidden mb-4 relative">
        <img
          :src="current.original_url"
          :alt="current.filename"
          class="w-full max-h-[55vh] object-contain bg-black"
        />
        <!-- Swipe hint overlays (shown on decision) -->
        <Transition name="fade">
          <div v-if="decision === 'delete'" class="absolute inset-0 bg-red-500/30 flex items-center justify-center">
            <span class="text-7xl">🗑</span>
          </div>
        </Transition>
        <Transition name="fade">
          <div v-if="decision === 'keep'" class="absolute inset-0 bg-green-500/30 flex items-center justify-center">
            <span class="text-7xl">✓</span>
          </div>
        </Transition>
      </div>

      <!-- Metadata strip -->
      <div class="w-full flex flex-wrap gap-3 text-xs text-gray-500 mb-4 px-1">
        <span v-if="current.taken_at">📅 {{ formatDate(current.taken_at) }}</span>
        <span v-if="current.camera">📷 {{ current.camera }}</span>
        <span v-if="current.width">{{ current.width }}×{{ current.height }}</span>
        <span v-if="current.quality_score != null" :class="qualityColor">
          ⭐ {{ Math.round(current.quality_score * 100) }}%
        </span>
      </div>

      <!-- Action buttons -->
      <div class="grid grid-cols-3 gap-3 w-full">
        <button
          class="flex flex-col items-center py-4 rounded-2xl bg-red-500/10 hover:bg-red-500/20 text-red-400 transition-colors font-medium gap-1"
          @click="decide('delete')"
        >
          <span class="text-2xl">🗑</span>
          <span class="text-sm">Delete</span>
          <span class="text-xs text-red-500/60">← or D</span>
        </button>

        <button
          class="flex flex-col items-center py-4 rounded-2xl bg-gray-800 hover:bg-gray-700 text-gray-400 transition-colors font-medium gap-1"
          @click="decide('skip')"
        >
          <span class="text-2xl">⏭</span>
          <span class="text-sm">Skip</span>
          <span class="text-xs text-gray-600">S</span>
        </button>

        <button
          class="flex flex-col items-center py-4 rounded-2xl bg-green-500/10 hover:bg-green-500/20 text-green-400 transition-colors font-medium gap-1"
          @click="decide('keep')"
        >
          <span class="text-2xl">✓</span>
          <span class="text-sm">Keep</span>
          <span class="text-xs text-green-500/60">→ or K</span>
        </button>
      </div>

      <!-- Undo -->
      <button
        v-if="history.length"
        class="mt-3 text-xs text-gray-600 hover:text-gray-400"
        @click="undo"
      >↩ Undo last</button>
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
const decision = ref(null)  // brief flash: 'keep' | 'delete' | null
const opts = ref({ screenshots: true, duplicates: true, low_quality: true })

const current = computed(() => queue.value[currentIndex.value] ?? null)

const reasonLabel = computed(() => ({
  screenshot: '📱 Screenshot',
  duplicate: '🔁 Duplicate',
  low_quality: '⚠️ Low quality',
}[current.value?.triage_reason] ?? ''))

const reasonClass = computed(() => ({
  screenshot: 'bg-purple-500/20 text-purple-400',
  duplicate: 'bg-yellow-500/20 text-yellow-400',
  low_quality: 'bg-red-500/20 text-red-400',
}[current.value?.triage_reason] ?? 'bg-gray-800 text-gray-400'))

const qualityColor = computed(() => {
  const q = current.value?.quality_score
  if (q == null) return ''
  return q >= 0.7 ? 'text-green-400' : q >= 0.4 ? 'text-yellow-400' : 'text-red-400'
})

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
  }, 180)
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

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.18s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
