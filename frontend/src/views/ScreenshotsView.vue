<template>
  <div>
    <div class="flex flex-wrap items-center gap-3 mb-5">
      <div>
        <h1 class="text-xl font-bold">
          Screenshots
          <span class="text-gray-500 font-normal text-base">({{ total }})</span>
        </h1>
        <p class="text-xs text-gray-500 mt-0.5">Auto-detected by screen dimensions and filename</p>
      </div>

      <div class="ml-auto flex gap-2 flex-wrap">
        <button
          class="btn-ghost text-sm"
          :disabled="scanning"
          @click="runScan"
        >
          {{ scanning ? 'Scanning…' : '🔍 Scan library' }}
        </button>
        <button
          v-if="photos.length"
          class="btn-ghost text-sm text-red-400 hover:text-red-300"
          @click="deleteAll"
        >
          🗑 Delete all screenshots
        </button>
      </div>
    </div>

    <!-- Scan result banner -->
    <div v-if="scanResult" class="card p-3 mb-4 flex items-center gap-3 text-sm">
      <span class="text-green-400">✓</span>
      Scanned {{ scanResult.scanned }} photos —
      found <strong>{{ scanResult.total_screenshots }}</strong> screenshots
      ({{ scanResult.updated }} newly flagged).
      <button class="ml-auto text-gray-500 hover:text-gray-300 text-xs" @click="scanResult = null">✕</button>
    </div>

    <div v-if="loading" class="flex justify-center py-20">
      <span class="text-gray-500 animate-pulse">Loading…</span>
    </div>

    <template v-else-if="photos.length">
      <!-- Batch controls -->
      <div class="flex items-center gap-2 mb-3">
        <button
          class="px-3 py-1.5 rounded-xl text-sm font-medium transition-colors"
          :class="sel.selecting.value ? 'bg-brand-500 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'"
          @click="sel.selecting.value ? sel.clear() : (sel.selecting.value = true)"
        >Select</button>
        <button
          v-if="sel.selecting.value"
          class="px-3 py-1.5 rounded-xl bg-gray-800 text-gray-400 hover:bg-gray-700 text-sm"
          @click="sel.selectAll(photos.map(p => p.id))"
        >All ({{ photos.length }})</button>
      </div>

      <PhotoGrid
        :photos="photos"
        :selection="sel"
        :selection-mode="sel.selecting.value"
        :show-upload-hint="false"
        @select="openModal"
      />

      <div ref="sentinel" class="h-10" />
    </template>

    <div v-else class="flex flex-col items-center py-20 text-gray-600">
      <span class="text-5xl mb-4">📱</span>
      <p class="mb-2">No screenshots detected.</p>
      <p class="text-sm">Run "Scan library" to check existing photos.</p>
    </div>

    <PhotoModal
      v-if="modalPhoto"
      :photo="modalPhoto"
      :has-prev="modalIndex > 0"
      :has-next="modalIndex < photos.length - 1"
      @close="modalPhoto = null"
      @delete="softDelete"
      @prev="navigate(-1)"
      @next="navigate(1)"
    />

    <BatchToolbar
      :count="sel.count.value"
      @delete="bulkDelete"
      @download="bulkDownload"
      @clear="sel.clear()"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { photosApi } from '../api/photos'
import { useSelection } from '../composables/useSelection'
import PhotoGrid from '../components/PhotoGrid.vue'
import PhotoModal from '../components/PhotoModal.vue'
import BatchToolbar from '../components/BatchToolbar.vue'

const photos = ref([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const scanning = ref(false)
const scanResult = ref(null)
const modalPhoto = ref(null)
const modalIndex = ref(-1)
const sentinel = ref(null)
const sel = useSelection()

async function load(reset = false) {
  if (loading.value) return
  loading.value = true
  try {
    const { data } = await photosApi.listScreenshots({ page: page.value, per_page: 50 })
    if (reset) photos.value = data.photos
    else photos.value.push(...data.photos)
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function runScan() {
  scanning.value = true
  try {
    const { data } = await photosApi.scanScreenshots()
    scanResult.value = data
    page.value = 1
    await load(true)
  } finally {
    scanning.value = false
  }
}

function openModal(photo) {
  if (sel.selecting.value) { sel.toggle(photo.id); return }
  modalIndex.value = photos.value.findIndex((p) => p.id === photo.id)
  modalPhoto.value = photo
}

function navigate(dir) {
  const next = modalIndex.value + dir
  if (next < 0 || next >= photos.value.length) return
  modalIndex.value = next
  modalPhoto.value = photos.value[next]
}

async function softDelete(id) {
  await photosApi.delete(id)
  photos.value = photos.value.filter((p) => p.id !== id)
  total.value--
  modalPhoto.value = null
}

async function deleteAll() {
  if (!confirm(`Send all ${total.value} screenshots to trash? (favorites are kept)`)) return
  // Server-side: trashes EVERY screenshot, not just the ones scrolled into view.
  const { data } = await photosApi.runCleanup({ screenshots: true })
  photos.value = []
  total.value = 0
  sel.clear()
  scanResult.value = { scanned: data.deleted, total_screenshots: 0, updated: data.deleted }
  await load(true)
}

async function bulkDelete() {
  await photosApi.bulkDelete(sel.ids.value)
  photos.value = photos.value.filter((p) => !sel.selected.value.has(p.id))
  total.value -= sel.count.value
  sel.clear()
}

async function bulkDownload() {
  const { data } = await photosApi.downloadZip(sel.ids.value)
  const url = URL.createObjectURL(data)
  const a = document.createElement('a'); a.href = url; a.download = 'screenshots.zip'; a.click()
  URL.revokeObjectURL(url)
}

let observer
onMounted(() => {
  load(true)
  observer = new IntersectionObserver(([entry]) => {
    if (entry.isIntersecting && photos.value.length < total.value && !loading.value) {
      page.value++; load()
    }
  })
  if (sentinel.value) observer.observe(sentinel.value)
})
onBeforeUnmount(() => observer?.disconnect())
</script>
