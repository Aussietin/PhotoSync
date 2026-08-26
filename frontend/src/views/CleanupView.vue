<template>
  <div class="max-w-3xl mx-auto space-y-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-extrabold tracking-tight text-white flex items-center gap-2">
          <span>Smart Cleanup</span>
          <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-brand-500/20 text-brand-300 border border-brand-400/20">
            One-Pass
          </span>
        </h1>
        <p class="text-sm text-gray-400 mt-1">
          Scan your entire library, score image quality, and clear space hogs in bulk.
          <span class="text-brand-300 font-medium">♥ Favorites are always protected</span>.
        </p>
      </div>

      <!-- Quick nav to other tidy up tools -->
      <div class="flex items-center gap-1.5 flex-wrap text-xs">
        <router-link to="/screenshots" class="chip-muted">📱 Screenshots</router-link>
        <router-link to="/duplicates" class="chip-muted">🔁 Duplicates</router-link>
        <router-link to="/bursts" class="chip-muted">📸 Bursts</router-link>
        <router-link to="/large" class="chip-muted">🎬 Large files</router-link>
      </div>
    </div>

    <!-- Step 1: Analyze Library -->
    <div class="card p-5 space-y-4 border-brand-500/20 bg-ink-900/90 shadow-glow">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 class="font-bold text-base text-gray-100 flex items-center gap-2">
            <span class="grid place-items-center w-6 h-6 rounded-full bg-brand-gradient text-white text-xs">1</span>
            Analyze Library
          </h2>
          <p class="text-xs text-gray-400 mt-1">
            Detects screenshots, scores sharpness/exposure, finds duplicates, and groups faces.
          </p>
        </div>
        <button class="btn-primary text-sm flex-shrink-0" :disabled="analyzing" @click="analyze">
          <Spinner v-if="analyzing" :size="16" />
          {{ analyzing ? 'Analyzing…' : '✨ Start Analysis' }}
        </button>
      </div>

      <div v-if="analyzeResult" class="text-xs sm:text-sm text-emerald-300 bg-emerald-500/10 border border-emerald-500/20 rounded-xl p-3.5 space-y-1">
        <div class="font-semibold flex items-center gap-1.5">
          <span>✓</span> Analysis complete — scanned {{ analyzeResult.scanned.toLocaleString() }} photos
        </div>
        <p class="text-gray-400 text-xs">
          Found <strong>{{ analyzeResult.screenshots }}</strong> screenshots,
          <strong>{{ analyzeResult.duplicates?.duplicates ?? 0 }}</strong> duplicates, and updated
          <strong>{{ analyzeResult.quality_recomputed }}</strong> quality scores.
          <template v-if="analyzeResult.face_model_available">
            Detected <strong>{{ analyzeResult.faces_found }}</strong> faces across
            <router-link to="/people" class="underline font-semibold text-brand-300">{{ analyzeResult.people?.total_people ?? 0 }} people</router-link>.
          </template>
        </p>
      </div>

      <div v-if="analyzing" class="space-y-2 bg-ink-850 p-3 rounded-xl border border-white/5">
        <div class="flex justify-between text-xs text-gray-400">
          <span>Clustering duplicate images & scoring quality…</span>
          <span v-if="job && job.percent != null" class="font-mono font-bold text-brand-300">{{ job.percent }}%</span>
        </div>
        <ProgressBar :value="(job && job.percent) || 10" />
      </div>
    </div>

    <!-- Step 2: Quality threshold -->
    <div class="card p-5 space-y-3">
      <div class="flex items-center justify-between">
        <h2 class="font-bold text-base text-gray-100 flex items-center gap-2">
          <span class="grid place-items-center w-6 h-6 rounded-full bg-brand-gradient text-white text-xs">2</span>
          Quality Threshold
        </h2>
        <span class="text-xs font-mono font-bold text-brand-300 bg-brand-500/15 px-2.5 py-1 rounded-full border border-brand-400/20">
          ≤ {{ Math.round(threshold * 100) }}% score
        </span>
      </div>
      <p class="text-xs text-gray-400">
        Photos scoring at or below this threshold are flagged as "low quality" (blurry or poorly exposed).
      </p>
      <div class="flex items-center gap-4 pt-1">
        <input
          v-model.number="threshold"
          type="range" min="0" max="0.6" step="0.05"
          class="flex-1 accent-brand-500 h-2 bg-ink-800 rounded-lg cursor-pointer"
          @change="loadSummary"
        />
      </div>
    </div>

    <!-- Step 3: Categories -->
    <div v-if="loading" class="flex justify-center py-10">
      <Spinner :size="28" label="Calculating library savings…" />
    </div>

    <div v-else-if="summary" class="space-y-4">
      <div class="flex items-center justify-between">
        <h2 class="font-bold text-base text-gray-100 flex items-center gap-2">
          <span class="grid place-items-center w-6 h-6 rounded-full bg-brand-gradient text-white text-xs">3</span>
          Select Categories to Clean
        </h2>
        <button
          class="text-xs text-gray-400 hover:text-white"
          @click="toggleSelectAll"
        >
          {{ anyPicked ? 'Deselect all' : 'Select all' }}
        </button>
      </div>

      <div class="grid gap-2.5">
        <CategoryCard
          label="Screenshots"
          icon="📱"
          :count="summary.screenshots.count"
          :bytes="summary.screenshots.bytes"
          :checked="picked.screenshots"
          badge="Dimensions"
          @toggle="picked.screenshots = !picked.screenshots"
          @clean="cleanOne({ screenshots: true }, 'screenshots')"
        >
          <template #hint>Exact device screen sizes. Favorite anything with credentials first.</template>
        </CategoryCard>

        <CategoryCard
          label="Near-Duplicates"
          icon="🔁"
          :count="summary.duplicates.count"
          :bytes="summary.duplicates.bytes"
          :checked="picked.duplicates"
          badge="Perceptual Hash"
          @toggle="picked.duplicates = !picked.duplicates"
          @clean="cleanOne({ duplicates: true }, 'duplicates')"
        >
          <template #hint>Keeps the sharpest version in each cluster and trashes the rest.</template>
        </CategoryCard>

        <CategoryCard
          :label="`Low Quality (≤ ${Math.round(threshold * 100)}%)`"
          icon="⚠️"
          :count="summary.low_quality.count"
          :bytes="summary.low_quality.bytes"
          :checked="picked.low_quality"
          badge="Blur & Exposure"
          @toggle="picked.low_quality = !picked.low_quality"
          @clean="cleanOne({ max_quality: threshold }, 'low_quality')"
        >
          <template #hint>Blurry, severely dark, or overblown frames.</template>
        </CategoryCard>

        <CategoryCard
          label="Dark / Underexposed"
          icon="🌑"
          :count="summary.dark.count"
          :bytes="summary.dark.bytes"
          :checked="picked.dark"
          badge="Luminance"
          @toggle="picked.dark = !picked.dark"
          @clean="cleanOne({ dark: true }, 'dark')"
        />

        <CategoryCard
          label="Blown Out / Overexposed"
          icon="☀️"
          :count="summary.overexposed.count"
          :bytes="summary.overexposed.bytes"
          :checked="picked.overexposed"
          badge="Luminance"
          @toggle="picked.overexposed = !picked.overexposed"
          @clean="cleanOne({ overexposed: true }, 'overexposed')"
        />

        <CategoryCard
          label="Low Resolution / Tiny"
          icon="🔬"
          :count="summary.low_res.count"
          :bytes="summary.low_res.bytes"
          :checked="picked.low_res"
          badge="Pixels"
          @toggle="picked.low_res = !picked.low_res"
          @clean="cleanOne({ low_res: true }, 'low_res')"
        />

        <CategoryCard
          label="Received / Memes"
          icon="📨"
          :count="summary.memes.count"
          :bytes="summary.memes.bytes"
          :checked="picked.memes"
          badge="No EXIF"
          @toggle="picked.memes = !picked.memes"
          @clean="cleanOne({ memes: true }, 'memes')"
        >
          <template #hint>WhatsApp forwards, downloads, and memes with no camera metadata.</template>
        </CategoryCard>

        <CategoryCard
          :label="`Large Files & Videos (≥ ${summary.large_threshold_mb} MB)`"
          icon="🎬"
          :count="summary.large.count"
          :bytes="summary.large.bytes"
          :checked="picked.large"
          badge="Space Hogs"
          @toggle="picked.large = !picked.large"
          @clean="cleanOne({ large: true }, 'large')"
        >
          <template #hint>Big videos and heavy assets — usually the biggest storage win.</template>
        </CategoryCard>
      </div>

      <!-- Undo Banner -->
      <div v-if="lastBatch" class="card p-3.5 flex items-center justify-between gap-3 bg-brand-500/10 border-brand-500/30">
        <span class="text-sm font-medium text-brand-200">✓ Trashed {{ lastDeleted.toLocaleString() }} photos.</span>
        <button class="btn-soft text-xs py-1 px-3" @click="undo">↩ Undo last cleanup</button>
      </div>

      <!-- Clean Selected Summary Card -->
      <div class="card p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-brand-500/30 bg-ink-850/90 shadow-glow">
        <div>
          <p class="font-bold text-base text-gray-100">Clean Selected Categories</p>
          <p class="text-xs text-gray-400 mt-1">
            <strong class="text-brand-300">{{ selectedStats.count.toLocaleString() }}</strong> photos selected •
            <strong class="text-emerald-400">{{ formatBytes(selectedStats.bytes) }}</strong> estimated reclaimable
          </p>
        </div>

        <button
          class="btn-primary text-sm py-2 px-5 flex-shrink-0"
          :disabled="!anyPicked || cleaning || selectedStats.count === 0"
          @click="cleanSelected"
        >
          <Spinner v-if="cleaning" :size="16" />
          {{ cleaning ? 'Moving to Trash…' : '🗑 Move Selected to Trash' }}
        </button>
      </div>

      <div class="p-3 bg-ink-900/40 rounded-xl border border-white/5 text-center text-xs text-gray-500 space-y-1">
        <p>
          Nothing is permanently removed — all items move to
          <router-link to="/trash" class="text-brand-400 hover:underline font-medium">Trash</router-link>
          for safe recovery.
        </p>
        <p>
          Prefer reviewing photos one-by-one?
          <router-link to="/triage" class="text-brand-400 hover:underline font-medium">Open Triage Mode →</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { photosApi } from '../api/photos'
import { useJob } from '../composables/useJob'
import Spinner from '../components/ui/Spinner.vue'
import ProgressBar from '../components/ui/ProgressBar.vue'
import { useToast } from '../composables/useToast'
import { useConfirm } from '../composables/useConfirm'

const { success, error: toastError } = useToast()
const { confirm } = useConfirm()

// Category Card Component
const CategoryCard = {
  props: ['label', 'icon', 'count', 'bytes', 'checked', 'badge'],
  emits: ['toggle', 'clean'],
  setup() {
    const fmt = (b) => {
      if (!b) return '0 B'
      if (b < 1048576) return `${(b / 1024).toFixed(0)} KB`
      if (b < 1073741824) return `${(b / 1048576).toFixed(1)} MB`
      return `${(b / 1073741824).toFixed(2)} GB`
    }
    return { fmt }
  },
  template: `
    <div
      class="card p-3.5 sm:p-4 flex items-center gap-3 transition-all duration-150"
      :class="checked ? 'bg-ink-850/90 border-brand-500/30 ring-1 ring-brand-500/20' : 'hover:border-white/10'"
    >
      <input
        type="checkbox"
        :checked="checked"
        class="accent-brand-500 w-4 h-4 rounded cursor-pointer flex-shrink-0"
        @change="$emit('toggle')"
      />
      <span class="text-2xl flex-shrink-0">{{ icon }}</span>
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 flex-wrap">
          <p class="font-semibold text-sm text-gray-200">{{ label }}</p>
          <span v-if="badge" class="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-white/5 text-gray-400 border border-white/5">{{ badge }}</span>
        </div>
        <p class="text-xs text-gray-400 mt-0.5">
          <strong class="text-gray-200 font-mono">{{ count.toLocaleString() }}</strong> photos •
          <span class="text-emerald-400 font-mono">{{ fmt(bytes) }}</span>
        </p>
        <p v-if="$slots.hint" class="text-xs text-gray-500 mt-1"><slot name="hint" /></p>
      </div>
      <button
        class="btn-ghost text-xs py-1.5 px-3 flex-shrink-0"
        :disabled="count === 0"
        @click="$emit('clean')"
      >
        Trash all
      </button>
    </div>
  `,
}

const analyzing = ref(false)
const analyzeResult = ref(null)
const loading = ref(false)
const cleaning = ref(false)
const threshold = ref(0.3)
const summary = ref(null)
const lastBatch = ref(null)
const lastDeleted = ref(0)
const picked = reactive({
  screenshots: true,
  duplicates: true,
  low_quality: false,
  dark: false,
  overexposed: false,
  low_res: false,
  memes: false,
  large: false,
})
const { job, track } = useJob()

const anyPicked = computed(() => Object.values(picked).some(Boolean))

const selectedStats = computed(() => {
  if (!summary.value) return { count: 0, bytes: 0 }
  let count = 0
  let bytes = 0
  const keys = [
    ['screenshots', 'screenshots'],
    ['duplicates', 'duplicates'],
    ['low_quality', 'low_quality'],
    ['dark', 'dark'],
    ['overexposed', 'overexposed'],
    ['low_res', 'low_res'],
    ['memes', 'memes'],
    ['large', 'large'],
  ]
  for (const [stateKey, sumKey] of keys) {
    if (picked[stateKey] && summary.value[sumKey]) {
      count += summary.value[sumKey].count || 0
      bytes += summary.value[sumKey].bytes || 0
    }
  }
  return { count, bytes }
})

function toggleSelectAll() {
  const newVal = !anyPicked.value
  for (const k in picked) {
    picked[k] = newVal
  }
}

onMounted(loadSummary)

async function loadSummary() {
  loading.value = true
  try {
    const { data } = await photosApi.cleanupSummary(threshold.value)
    summary.value = data
  } finally {
    loading.value = false
  }
}

async function analyze() {
  analyzing.value = true
  analyzeResult.value = null
  try {
    const { data } = await photosApi.analyzeLibrary()
    await track(data.job_id, {
      interval: 1500,
      onDone: async (j) => {
        analyzeResult.value = j.result
        analyzing.value = false
        await loadSummary()
        success('Library analysis complete')
      },
      onError: (j) => {
        toastError('Analyze failed: ' + (j.message || 'error'))
        analyzing.value = false
      },
    })
  } catch (e) {
    analyzing.value = false
  }
}

function recordBatch(res) {
  if (res?.batch && res.deleted) {
    lastBatch.value = res.batch
    lastDeleted.value = res.deleted
  }
}

async function cleanOne(filters, key) {
  const cat = summary.value[key]
  if (!cat || cat.count === 0) return
  const ok = await confirm({
    title: `Move ${cat.count.toLocaleString()} photos to Trash?`,
    message: 'Favorites are always protected. You can review or restore from Trash anytime.',
    confirmText: 'Move to Trash',
    danger: true,
  })
  if (!ok) return
  const { data } = await photosApi.runCleanup(filters)
  recordBatch(data)
  await loadSummary()
  if (data.deleted) success(`Moved ${data.deleted.toLocaleString()} photos to Trash`)
}

async function cleanSelected() {
  if (!anyPicked.value) return
  const filters = {
    screenshots: picked.screenshots,
    duplicates: picked.duplicates,
    dark: picked.dark,
    overexposed: picked.overexposed,
    low_res: picked.low_res,
    memes: picked.memes,
    large: picked.large,
    max_quality: picked.low_quality ? threshold.value : null,
  }
  const n = selectedStats.value.count
  const ok = await confirm({
    title: `Move ${n.toLocaleString()} selected photos to Trash?`,
    message: 'Favorites are kept safe. All items can be restored from Trash.',
    confirmText: 'Move to Trash',
    danger: true,
  })
  if (!ok) return
  cleaning.value = true
  try {
    const { data } = await photosApi.runCleanup(filters)
    recordBatch(data)
    await loadSummary()
    if (data.deleted) success(`Moved ${data.deleted.toLocaleString()} photos to Trash`)
  } finally {
    cleaning.value = false
  }
}

async function undo() {
  if (!lastBatch.value) return
  await photosApi.undoCleanup(lastBatch.value)
  lastBatch.value = null
  await loadSummary()
  success('Last cleanup undone')
}

function formatBytes(b) {
  if (!b) return '0 B'
  if (b < 1048576) return `${(b / 1024).toFixed(0)} KB`
  if (b < 1073741824) return `${(b / 1048576).toFixed(1)} MB`
  return `${(b / 1073741824).toFixed(2)} GB`
}
</script>
