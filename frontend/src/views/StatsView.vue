<template>
  <div class="space-y-6">
    <!-- Header Banner -->
    <div class="flex flex-wrap items-center justify-between gap-3 bg-ink-900/60 p-4 rounded-2xl border border-white/5 backdrop-blur-md">
      <div>
        <h1 class="text-xl font-extrabold tracking-tight text-white flex items-center gap-2">
          <span>Library Analytics & Storage</span>
        </h1>
        <p class="text-xs text-gray-400 mt-1">
          Overview of assets, storage breakdown, quality scores, and device distributions.
        </p>
      </div>
    </div>

    <!-- Skeleton state -->
    <div v-if="loading" class="space-y-6">
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <div v-for="i in 6" :key="i" class="card p-4 flex flex-col items-center gap-2">
          <Skeleton width="2rem" height="2rem" rounded="rounded-xl" />
          <Skeleton width="3.5rem" height="1.1rem" />
          <Skeleton width="2.5rem" height="0.7rem" />
        </div>
      </div>
      <div class="card p-5 space-y-3">
        <Skeleton width="10rem" height="0.9rem" />
        <div v-for="i in 6" :key="i" class="flex items-center gap-3">
          <Skeleton width="4rem" height="0.7rem" />
          <Skeleton :width="`${30 + (i * 9) % 60}%`" height="1rem" rounded="rounded-full" />
        </div>
      </div>
    </div>

    <template v-else-if="stats">
      <!-- Summary cards -->
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard label="Total Media" :value="stats.total_photos.toLocaleString()" icon="🖼️" />
        <StatCard label="Storage" :value="formatBytes(stats.total_size_bytes)" icon="💾" />
        <StatCard label="Favorites" :value="stats.favorites.toLocaleString()" icon="♥" />
        <StatCard label="Duplicates" :value="stats.duplicates.toLocaleString()" icon="🔁" />
        <StatCard label="GPS Located" :value="stats.with_gps.toLocaleString()" icon="📍" />
        <StatCard label="In Trash" :value="stats.in_trash.toLocaleString()" icon="🗑" />
      </div>

      <!-- Monthly chart -->
      <div class="card p-5 bg-ink-900/80 border-white/5 shadow-md">
        <h2 class="text-xs font-bold text-gray-300 uppercase tracking-wider mb-4 flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-brand-400" />
          Photos by Month
        </h2>
        <div v-if="chartData.length" class="space-y-2.5">
          <div v-for="item in chartData" :key="item.month" class="flex items-center gap-3">
            <span class="text-xs text-gray-400 w-16 flex-shrink-0 text-right font-medium">{{ formatMonth(item.month) }}</span>
            <div class="flex-1 bg-ink-850 rounded-full h-3.5 overflow-hidden border border-white/5">
              <div
                class="h-full bg-brand-gradient rounded-full transition-all duration-500 shadow-glow"
                :style="{ width: barWidth(item.count) }"
              />
            </div>
            <span class="text-xs font-mono font-semibold text-gray-300 w-12 text-right flex-shrink-0">{{ item.count }}</span>
          </div>
        </div>
        <p v-else class="text-gray-500 text-xs">No dated photos recorded.</p>
      </div>

      <!-- Top tags + Cameras side by side -->
      <div class="grid sm:grid-cols-2 gap-4">
        <div class="card p-5 bg-ink-900/80 border-white/5 shadow-md">
          <h2 class="text-xs font-bold text-gray-300 uppercase tracking-wider mb-4 flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-purple-400" />
            Top Tags & Labels
          </h2>
          <div class="space-y-2.5">
            <div v-for="t in stats.top_tags" :key="t.name" class="flex items-center gap-2">
              <span class="text-xs font-medium text-gray-300 flex-1 truncate">{{ t.name }}</span>
              <div class="w-28 bg-ink-850 rounded-full h-2 overflow-hidden border border-white/5">
                <div
                  class="h-full bg-purple-500/80 rounded-full"
                  :style="{ width: pct(t.count, stats.top_tags[0]?.count) }"
                />
              </div>
              <span class="text-xs font-mono text-gray-400 w-8 text-right">{{ t.count }}</span>
            </div>
            <p v-if="!stats.top_tags.length" class="text-gray-500 text-xs">No tags recorded.</p>
          </div>
        </div>

        <div class="card p-5 bg-ink-900/80 border-white/5 shadow-md">
          <h2 class="text-xs font-bold text-gray-300 uppercase tracking-wider mb-4 flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-emerald-400" />
            Cameras & Devices
          </h2>
          <div class="space-y-2.5">
            <div v-for="c in stats.cameras" :key="c.camera" class="flex items-center gap-2">
              <span class="text-xs font-medium text-gray-300 flex-1 truncate">{{ c.camera }}</span>
              <div class="w-28 bg-ink-850 rounded-full h-2 overflow-hidden border border-white/5">
                <div
                  class="h-full bg-emerald-500/80 rounded-full"
                  :style="{ width: pct(c.count, stats.cameras[0]?.count) }"
                />
              </div>
              <span class="text-xs font-mono text-gray-400 w-8 text-right">{{ c.count }}</span>
            </div>
            <p v-if="!stats.cameras.length" class="text-gray-500 text-xs">No camera metadata recorded.</p>
          </div>
        </div>
      </div>

      <!-- Quality Score -->
      <div v-if="stats.avg_quality != null" class="card p-5 bg-ink-900/80 border-white/5 shadow-md">
        <h2 class="text-xs font-bold text-gray-300 uppercase tracking-wider mb-3 flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-amber-400" />
          Average Image Quality (Sharpness & Exposure)
        </h2>
        <div class="flex items-center gap-4">
          <div class="flex-1 bg-ink-850 rounded-full h-3.5 overflow-hidden border border-white/5">
            <div
              class="h-full rounded-full transition-all"
              :class="qualityBar"
              :style="{ width: `${stats.avg_quality * 100}%` }"
            />
          </div>
          <span class="text-base font-extrabold font-mono" :class="qualityText">{{ Math.round(stats.avg_quality * 100) }}%</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { statsApi } from '../api/photos'
import Skeleton from '../components/ui/Skeleton.vue'

const StatCard = {
  props: ['label', 'value', 'icon'],
  template: `
    <div class="card p-4 text-center group bg-ink-900/85 border-white/5 hover:border-white/20 transition-all shadow-md">
      <div class="w-10 h-10 mx-auto mb-2 grid place-items-center text-xl rounded-xl bg-ink-800 border border-white/5 transition-transform group-hover:scale-110">{{ icon }}</div>
      <div class="text-lg font-extrabold text-gray-100 font-mono">{{ value }}</div>
      <div class="text-[11px] text-gray-400 mt-0.5 font-medium">{{ label }}</div>
    </div>
  `,
}

const stats = ref(null)
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await statsApi.get()
    stats.value = data
  } finally {
    loading.value = false
  }
})

const chartData = computed(() => {
  if (!stats.value) return []
  return [...stats.value.photos_by_month].reverse()
})

const maxCount = computed(() => Math.max(...(chartData.value.map((d) => d.count)), 1))

function barWidth(count) { return `${(count / maxCount.value) * 100}%` }
function pct(count, max) { return max ? `${(count / max) * 100}%` : '0%' }

const qualityBar = computed(() => {
  const q = stats.value?.avg_quality
  if (q == null) return ''
  if (q >= 0.7) return 'bg-emerald-500'
  if (q >= 0.4) return 'bg-amber-500'
  return 'bg-rose-500'
})
const qualityText = computed(() => {
  const q = stats.value?.avg_quality
  if (q == null) return ''
  if (q >= 0.7) return 'text-emerald-400'
  if (q >= 0.4) return 'text-amber-400'
  return 'text-rose-400'
})

function formatBytes(b) {
  if (!b) return '0 B'
  if (b < 1024) return `${b} B`
  if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`
  if (b < 1073741824) return `${(b / 1048576).toFixed(1)} MB`
  return `${(b / 1073741824).toFixed(2)} GB`
}

function formatMonth(key) {
  if (!key) return '?'
  const [y, m] = key.split('-')
  return new Date(+y, +m - 1).toLocaleString(undefined, { month: 'short', year: '2-digit' })
}
</script>
