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

    <PhotoGridSkeleton v-if="loading && !photos.length" :count="18" />

    <template v-else-if="photos.length">
      <!-- Batch controls -->
      <div class="flex items-center gap-2 mb-3">
        <button
          class="text-sm"
          :class="sel.selecting.value ? 'chip-active' : 'chip-muted'"
          @click="sel.selecting.value ? sel.clear() : (sel.selecting.value = true)"
        >Select</button>
        <button
          v-if="sel.selecting.value"
          class="chip-muted text-sm"
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

    <EmptyState
      v-else
      icon="📱"
      title="No screenshots detected"
      subtitle="Run a library scan to find existing screenshots by their dimensions and filenames."
    >
      <template #action>
        <button class="btn-primary text-sm" :disabled="scanning" @click="runScan">
          {{ scanning ? 'Scanning…' : '🔍 Scan library' }}
        </button>
      </template>
    </EmptyState>

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
import PhotoGridSkeleton from '../components/ui/PhotoGridSkeleton.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import PhotoModal from '../components/PhotoModal.vue'
import BatchToolbar from '../components/BatchToolbar.vue'
import { useToast } from '../composables/useToast'
import { useConfirm } from '../composables/useConfirm'

const { success } = useToast()
const { confirm } = useConfirm()

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
  const ok = await confirm({
    title: `Move all ${total.value} screenshots to Trash?`,
    message: 'Favorites are always kept. You can restore from Trash later.',
    confirmText: 'Move to Trash',
    danger: true,
  })
  if (!ok) return
  // Server-side: trashes EVERY screenshot, not just the ones scrolled into view.
  const { data } = await photosApi.runCleanup({ screenshots: true })
  photos.value = []
  total.value = 0
  sel.clear()
  scanResult.value = { scanned: data.deleted, total_screenshots: 0, updated: data.deleted }
  success(`Moved ${data.deleted} screenshots to Trash`)
  await load(true)
}

async function bulkDelete() {
  const n = sel.count.value
  await photosApi.bulkDelete(sel.ids.value)
  photos.value = photos.value.filter((p) => !sel.selected.value.has(p.id))
  total.value -= n
  sel.clear()
  success(`Moved ${n} to Trash`)
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
