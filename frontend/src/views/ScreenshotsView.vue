<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3 bg-ink-900/60 p-4 rounded-2xl border border-white/5 backdrop-blur-md">
      <div>
        <h1 class="text-xl font-extrabold tracking-tight text-white flex items-center gap-2">
          <span>Screenshots</span>
          <span class="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-400/20">
            {{ total.toLocaleString() }}
          </span>
        </h1>
        <p class="text-xs text-gray-400 mt-1">
          Auto-detected by device screen dimensions and system file naming conventions.
        </p>
      </div>

      <div class="flex items-center gap-2 flex-wrap">
        <button
          class="btn-ghost text-xs sm:text-sm py-2 px-3"
          :disabled="scanning"
          @click="runScan"
        >
          <Spinner v-if="scanning" :size="16" />
          {{ scanning ? 'Scanning…' : '🔍 Scan Library' }}
        </button>
        <button
          v-if="photos.length"
          class="btn-danger text-xs sm:text-sm py-2 px-4 shadow-sm"
          @click="deleteAll"
        >
          🗑 Trash All Screenshots
        </button>
      </div>
    </div>

    <!-- Scan result banner -->
    <div v-if="scanResult" class="card p-3.5 bg-emerald-500/10 border-emerald-500/30 flex items-center gap-3 text-xs sm:text-sm text-emerald-300">
      <span class="font-bold">✓</span>
      <span>
        Scanned <strong>{{ scanResult.scanned }}</strong> photos — found <strong>{{ scanResult.total_screenshots }}</strong> screenshots ({{ scanResult.updated }} newly flagged).
      </span>
      <button class="ml-auto text-gray-400 hover:text-white text-xs p-1" @click="scanResult = null">✕</button>
    </div>

    <PhotoGridSkeleton v-if="loading && !photos.length" :count="18" />

    <template v-else-if="photos.length">
      <!-- Batch & Mode bar -->
      <div class="flex items-center justify-between gap-2">
        <div class="flex items-center gap-2">
          <button
            class="btn-ghost text-xs py-1.5 px-3"
            :class="sel.selecting.value && 'bg-brand-500/20 border-brand-400/40 text-brand-200'"
            @click="sel.selecting.value ? sel.clear() : (sel.selecting.value = true)"
          >
            {{ sel.selecting.value ? 'Cancel' : 'Select' }}
          </button>
          <button
            v-if="sel.selecting.value"
            class="btn-ghost text-xs py-1.5 px-3"
            @click="sel.selectAll(photos.map(p => p.id))"
          >
            Select All ({{ photos.length }})
          </button>
        </div>
      </div>

      <PhotoGrid
        :photos="photos"
        :selection="sel"
        :selection-mode="sel.selecting.value"
        :show-upload-hint="false"
        @select="openModal"
        @toggle-favorite="toggleFavorite"
      />

      <div ref="sentinel" class="h-10" />
    </template>

    <EmptyState
      v-else
      icon="📱"
      title="No screenshots detected"
      subtitle="Run a quick library scan to automatically flag screenshot files by screen geometry."
    >
      <template #action>
        <button class="btn-primary text-sm" :disabled="scanning" @click="runScan">
          {{ scanning ? 'Scanning…' : '🔍 Scan Library' }}
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
      @toggle-favorite="toggleFavorite"
      @prev="navigate(-1)"
      @next="navigate(1)"
    />

    <BatchToolbar
      :count="sel.count.value"
      @favorite="bulkFavorite"
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
import Spinner from '../components/ui/Spinner.vue'
import PhotoModal from '../components/PhotoModal.vue'
import BatchToolbar from '../components/BatchToolbar.vue'
import { useToast } from '../composables/useToast'
import { useConfirm } from '../composables/useConfirm'

const { success, error: toastError } = useToast()
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
    success(`Found ${data.total_screenshots} screenshots`)
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
  success('Moved screenshot to Trash')
}

async function deleteAll() {
  const ok = await confirm({
    title: `Move all ${total.value} screenshots to Trash?`,
    message: 'Favorites are always protected and will be kept. You can restore from Trash later.',
    confirmText: 'Move to Trash',
    danger: true,
  })
  if (!ok) return
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
  success(`Moved ${n} screenshots to Trash`)
}

async function bulkDownload() {
  try {
    const { data } = await photosApi.downloadZip(sel.ids.value)
    const url = URL.createObjectURL(data)
    const a = document.createElement('a')
    a.href = url
    a.download = 'screenshots.zip'
    a.click()
    URL.revokeObjectURL(url)
    success('Downloading screenshots ZIP')
  } catch {
    toastError('Could not export screenshots ZIP')
  }
}

async function toggleFavorite(id) {
  const { data } = await photosApi.toggleFavorite(id)
  const photo = photos.value.find((p) => p.id === id)
  if (photo) photo.is_favorite = data.is_favorite
  if (modalPhoto.value?.id === id) modalPhoto.value = { ...modalPhoto.value, is_favorite: data.is_favorite }
}

async function bulkFavorite() {
  const n = sel.count.value
  await photosApi.bulkFavorite(sel.ids.value)
  photos.value.forEach((p) => { if (sel.selected.value.has(p.id)) p.is_favorite = true })
  sel.clear()
  success(`Added ${n} to Favorites (protected from cleanup)`)
}

let observer
onMounted(() => {
  load(true)
  observer = new IntersectionObserver(([entry]) => {
    if (entry.isIntersecting && photos.value.length < total.value && !loading.value) {
      page.value++
      load()
    }
  })
  if (sentinel.value) observer.observe(sentinel.value)
})
onBeforeUnmount(() => observer?.disconnect())
</script>
