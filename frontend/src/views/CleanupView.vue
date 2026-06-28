<template>
  <div class="max-w-2xl mx-auto space-y-6">
    <div>
      <h1 class="text-xl font-bold">Smart Cleanup</h1>
      <p class="text-sm text-gray-500 mt-1">
        Find and remove screenshots, duplicates, and low-quality shots across your
        entire library in one pass. Favorites are always protected.
      </p>
    </div>

    <!-- Step 1: Analyze -->
    <div class="card p-5 space-y-3">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="font-semibold">1. Analyze library</h2>
          <p class="text-xs text-gray-500 mt-0.5">
            Detects screenshots, scores quality (blur/exposure), and clusters near-duplicates.
          </p>
        </div>
        <button class="btn-primary text-sm flex-shrink-0" :disabled="analyzing" @click="analyze">
          {{ analyzing ? 'Analyzing…' : 'Analyze' }}
        </button>
      </div>
      <div v-if="analyzeResult" class="text-sm text-green-400 bg-green-500/10 rounded-xl px-4 py-2">
        ✓ Scanned {{ analyzeResult.scanned.toLocaleString() }} photos —
        {{ analyzeResult.screenshots }} screenshots,
        {{ analyzeResult.duplicates?.duplicates ?? 0 }} duplicates,
        {{ analyzeResult.quality_recomputed }} quality scores updated.
      </div>
      <p v-if="analyzing" class="text-xs text-gray-500 animate-pulse">
        Reading thumbnails and clustering hashes — this can take a few minutes for large libraries.
      </p>
    </div>

    <!-- Step 2: Threshold -->
    <div class="card p-5 space-y-3">
      <h2 class="font-semibold">2. Quality threshold</h2>
      <p class="text-xs text-gray-500">
        Photos scoring at or below this are flagged "low quality" (blurry / poorly exposed).
      </p>
      <div class="flex items-center gap-4">
        <input
          v-model.number="threshold"
          type="range" min="0" max="0.6" step="0.05"
          class="flex-1 accent-brand-500"
          @change="loadSummary"
        />
        <span class="text-sm font-mono text-gray-300 w-12 text-right">{{ Math.round(threshold * 100) }}%</span>
      </div>
    </div>

    <!-- Step 3: Categories -->
    <div v-if="loading" class="flex justify-center py-10">
      <span class="text-gray-500 animate-pulse">Loading summary…</span>
    </div>

    <div v-else-if="summary" class="space-y-3">
      <h2 class="font-semibold">3. Choose what to clean</h2>

      <CategoryRow
        label="Screenshots"
        icon="📱"
        :count="summary.screenshots.count"
        :bytes="summary.screenshots.bytes"
        :checked="picked.screenshots"
        @toggle="picked.screenshots = !picked.screenshots"
        @clean="cleanOne({ screenshots: true }, 'screenshots')"
      />
      <CategoryRow
        label="Duplicates"
        icon="🔁"
        :count="summary.duplicates.count"
        :bytes="summary.duplicates.bytes"
        :checked="picked.duplicates"
        @toggle="picked.duplicates = !picked.duplicates"
        @clean="cleanOne({ duplicates: true }, 'duplicates')"
      />
      <CategoryRow
        :label="`Low quality (≤ ${Math.round(threshold * 100)}%)`"
        icon="⚠️"
        :count="summary.low_quality.count"
        :bytes="summary.low_quality.bytes"
        :checked="picked.low_quality"
        @toggle="picked.low_quality = !picked.low_quality"
        @clean="cleanOne({ max_quality: threshold }, 'low_quality')"
      />

      <!-- Combined action -->
      <div class="card p-4 flex items-center gap-3 border border-gray-700">
        <div class="flex-1">
          <p class="font-medium text-sm">Clean everything selected</p>
          <p class="text-xs text-gray-500 mt-0.5">
            {{ summary.total_reclaimable.count.toLocaleString() }} photos •
            {{ formatBytes(summary.total_reclaimable.bytes) }} reclaimable in total
          </p>
        </div>
        <button
          class="btn-primary text-sm flex-shrink-0 disabled:opacity-40"
          :disabled="!anyPicked || cleaning"
          @click="cleanSelected"
        >
          {{ cleaning ? 'Cleaning…' : 'Trash selected' }}
        </button>
      </div>

      <p class="text-xs text-gray-600 text-center pt-2">
        Nothing is permanently deleted — items go to
        <router-link to="/trash" class="text-brand-400 hover:underline">Trash</router-link>,
        where you can restore or empty them. Prefer reviewing one-by-one?
        <router-link to="/triage" class="text-brand-400 hover:underline">Triage mode</router-link>.
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { photosApi } from '../api/photos'

// Inline category row component
const CategoryRow = {
  props: ['label', 'icon', 'count', 'bytes', 'checked'],
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
    <div class="card p-4 flex items-center gap-3">
      <input type="checkbox" :checked="checked" class="accent-brand-500 w-4 h-4" @change="$emit('toggle')" />
      <span class="text-2xl">{{ icon }}</span>
      <div class="flex-1 min-w-0">
        <p class="font-medium text-sm text-gray-200">{{ label }}</p>
        <p class="text-xs text-gray-500">{{ count.toLocaleString() }} photos • {{ fmt(bytes) }}</p>
      </div>
      <button
        class="text-sm px-3 py-1.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 disabled:opacity-40 flex-shrink-0"
        :disabled="count === 0"
        @click="$emit('clean')"
      >Trash all</button>
    </div>
  `,
}

const analyzing = ref(false)
const analyzeResult = ref(null)
const loading = ref(false)
const cleaning = ref(false)
const threshold = ref(0.3)
const summary = ref(null)
const picked = reactive({ screenshots: true, duplicates: true, low_quality: false })

const anyPicked = computed(() => picked.screenshots || picked.duplicates || picked.low_quality)

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
    const { data } = await photosApi.analyzeLibrary(true)
    analyzeResult.value = data
    await loadSummary()
  } finally {
    analyzing.value = false
  }
}

async function cleanOne(filters, key) {
  const cat = summary.value[key]
  if (!cat || cat.count === 0) return
  if (!confirm(`Send ${cat.count.toLocaleString()} photos to trash? (favorites kept)`)) return
  await photosApi.runCleanup(filters)
  await loadSummary()
}

async function cleanSelected() {
  if (!anyPicked.value) return
  const filters = {
    screenshots: picked.screenshots,
    duplicates: picked.duplicates,
    max_quality: picked.low_quality ? threshold.value : null,
  }
  const n = summary.value.total_reclaimable.count
  if (!confirm(`Send up to ${n.toLocaleString()} photos to trash? (favorites kept)`)) return
  cleaning.value = true
  try {
    await photosApi.runCleanup(filters)
    await loadSummary()
  } finally {
    cleaning.value = false
  }
}

function formatBytes(b) {
  if (!b) return '0 B'
  if (b < 1048576) return `${(b / 1024).toFixed(0)} KB`
  if (b < 1073741824) return `${(b / 1048576).toFixed(1)} MB`
  return `${(b / 1073741824).toFixed(2)} GB`
}
</script>
