<template>
  <div class="space-y-6">
    <h1 class="text-xl font-bold">Statistics</h1>

    <div v-if="loading" class="flex justify-center py-20">
      <span class="text-gray-500 animate-pulse">Loading…</span>
    </div>

    <template v-else-if="stats">
      <!-- Summary cards -->
      <div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard label="Photos" :value="stats.total_photos.toLocaleString()" icon="🖼️" />
        <StatCard label="Storage" :value="formatBytes(stats.total_size_bytes)" icon="💾" />
        <StatCard label="Favorites" :value="stats.favorites.toLocaleString()" icon="♥" />
        <StatCard label="Duplicates" :value="stats.duplicates.toLocaleString()" icon="🔁" />
        <StatCard label="With GPS" :value="stats.with_gps.toLocaleString()" icon="📍" />
        <StatCard label="In Trash" :value="stats.in_trash.toLocaleString()" icon="🗑" />
      </div>

      <!-- Monthly chart -->
      <div class="card p-5">
        <h2 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Photos per month</h2>
        <div v-if="chartData.length" class="space-y-2">
          <div v-for="item in chartData" :key="item.month" class="flex items-center gap-3">
            <span class="text-xs text-gray-500 w-16 flex-shrink-0 text-right">{{ formatMonth(item.month) }}</span>
            <div class="flex-1 bg-gray-800 rounded-full h-4 overflow-hidden">
              <div
                class="h-full bg-brand-500 rounded-full transition-all duration-500"
                :style="{ width: barWidth(item.count) }"
              />
            </div>
            <span class="text-xs text-gray-400 w-10 text-right flex-shrink-0">{{ item.count }}</span>
          </div>
        </div>
        <p v-else class="text-gray-600 text-sm">No dated photos yet.</p>
      </div>

      <!-- Top tags + Cameras side by side -->
      <div class="grid sm:grid-cols-2 gap-4">
        <div class="card p-5">
          <h2 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Top tags</h2>
          <div class="space-y-2">
            <div v-for="t in stats.top_tags" :key="t.name" class="flex items-center gap-2">
              <span class="text-sm text-gray-300 flex-1 truncate">{{ t.name }}</span>
              <div class="w-24 bg-gray-800 rounded-full h-2 overflow-hidden">
                <div
                  class="h-full bg-brand-500/70 rounded-full"
                  :style="{ width: pct(t.count, stats.top_tags[0]?.count) }"
                />
              </div>
              <span class="text-xs text-gray-500 w-8 text-right">{{ t.count }}</span>
            </div>
            <p v-if="!stats.top_tags.length" class="text-gray-600 text-sm">No tags yet.</p>
          </div>
        </div>

        <div class="card p-5">
          <h2 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Cameras</h2>
          <div class="space-y-2">
            <div v-for="c in stats.cameras" :key="c.camera" class="flex items-center gap-2">
              <span class="text-sm text-gray-300 flex-1 truncate">{{ c.camera }}</span>
              <div class="w-24 bg-gray-800 rounded-full h-2 overflow-hidden">
                <div
                  class="h-full bg-green-500/70 rounded-full"
                  :style="{ width: pct(c.count, stats.cameras[0]?.count) }"
                />
              </div>
              <span class="text-xs text-gray-500 w-8 text-right">{{ c.count }}</span>
            </div>
            <p v-if="!stats.cameras.length" class="text-gray-600 text-sm">No camera data.</p>
          </div>
        </div>
      </div>

      <!-- Quality -->
      <div v-if="stats.avg_quality != null" class="card p-5">
        <h2 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Average quality score</h2>
        <div class="flex items-center gap-4">
          <div class="flex-1 bg-gray-800 rounded-full h-4 overflow-hidden">
            <div
              class="h-full rounded-full transition-all"
              :class="qualityColor"
              :style="{ width: `${stats.avg_quality * 100}%` }"
            />
          </div>
          <span class="text-lg font-bold" :class="qualityColor">{{ Math.round(stats.avg_quality * 100) }}%</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { statsApi } from '../api/photos'

// Inline stat card
const StatCard = {
  props: ['label', 'value', 'icon'],
  template: `
    <div class="card p-4 text-center">
      <div class="text-2xl mb-1">{{ icon }}</div>
      <div class="text-lg font-bold text-gray-100">{{ value }}</div>
      <div class="text-xs text-gray-500 mt-0.5">{{ label }}</div>
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

const qualityColor = computed(() => {
  const q = stats.value?.avg_quality
  if (q == null) return ''
  if (q >= 0.7) return 'bg-green-500 text-green-400'
  if (q >= 0.4) return 'bg-yellow-500 text-yellow-400'
  return 'bg-red-500 text-red-400'
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
