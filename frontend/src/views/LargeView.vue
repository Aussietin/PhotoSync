<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3 bg-ink-900/60 p-4 rounded-2xl border border-white/5 backdrop-blur-md">
      <div>
        <h1 class="text-xl font-extrabold tracking-tight text-white flex items-center gap-2">
          <span>Large Space Hogs</span>
          <span class="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-pink-500/20 text-pink-300 border border-pink-400/20">
            {{ total.toLocaleString() }} files ({{ formatBytes(totalBytes) }})
          </span>
        </h1>
        <p class="text-xs text-gray-400 mt-1">
          High-bitrate videos, 4K clips, and massive assets (≥ {{ thresholdMb }} MB) sorted largest to smallest.
        </p>
      </div>

      <div class="flex items-center gap-2 flex-wrap">
        <button
          v-if="photos.length"
          class="btn-danger text-xs sm:text-sm py-2 px-4 shadow-sm"
          @click="deleteAll"
        >
          🗑 Trash All Large Files
        </button>
      </div>
    </div>

    <!-- Filter chips for large files -->
    <div class="flex items-center gap-1.5 overflow-x-auto no-scrollbar">
      <button
        class="chip"
        :class="filter === 'all' ? 'chip-active' : 'chip-muted'"
        @click="filter = 'all'"
      >
        All ({{ total }})
      </button>
      <button
        class="chip"
        :class="filter === 'videos' ? 'chip-active text-sky-300 border-sky-500/40 bg-sky-500/20' : 'chip-muted'"
        @click="filter = 'videos'"
      >
        🎬 Videos Only ({{ videoCount }})
      </button>
      <button
        class="chip"
        :class="filter === 'photos' ? 'chip-active' : 'chip-muted'"
        @click="filter = 'photos'"
      >
        🖼️ Photos Only ({{ photoCount }})
      </button>
    </div>

    <PhotoGridSkeleton v-if="loading && !photos.length" :count="18" />

    <template v-else-if="filteredPhotos.length">
      <!-- Batch Controls Bar -->
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
            @click="sel.selectAll(filteredPhotos.map(p => p.id))"
          >
            Select All ({{ filteredPhotos.length }})
          </button>
        </div>
      </div>

      <PhotoGrid
        :photos="filteredPhotos"
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
      icon="🎬"
      title="No large files detected"
      subtitle="No media exceeds the current threshold. Once high-res videos or big files are imported, they'll appear here."
    />

    <PhotoModal
      v-if="modalPhoto"
      :photo="modalPhoto"
      :has-prev="modalIndex > 0"
      :has-next="modalIndex < filteredPhotos.length - 1"
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
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { photosApi } from '../api/photos'
import { useSelection } from '../composables/useSelection'
import PhotoGrid from '../components/PhotoGrid.vue'
import PhotoGridSkeleton from '../components/ui/PhotoGridSkeleton.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import PhotoModal from '../components/PhotoModal.vue'
import BatchToolbar from '../components/BatchToolbar.vue'
import { useToast } from '../composables/useToast'
import { useConfirm } from '../composables/useConfirm'

const { success, error: toastError } = useToast()
const { confirm } = useConfirm()

const photos = ref([])
const total = ref(0)
const totalBytes = ref(0)
const thresholdMb = ref(25)
const page = ref(1)
const loading = ref(false)
const filter = ref('all')
const modalPhoto = ref(null)
const modalIndex = ref(-1)
const sentinel = ref(null)
const sel = useSelection()

const videoCount = computed(() => photos.value.filter((p) => p.is_video).length)
const photoCount = computed(() => photos.value.filter((p) => !p.is_video).length)

const filteredPhotos = computed(() => {
  if (filter.value === 'videos') return photos.value.filter((p) => p.is_video)
  if (filter.value === 'photos') return photos.value.filter((p) => !p.is_video)
  return photos.value
})

async function load(reset = false) {
  if (loading.value) return
  loading.value = true
  try {
    const { data } = await photosApi.listLarge({ page: page.value, per_page: 50 })
    if (reset) photos.value = data.photos
    else photos.value.push(...data.photos)
    total.value = data.total
    totalBytes.value = data.total_bytes
    thresholdMb.value = data.threshold_mb
  } finally {
    loading.value = false
  }
}

function openModal(photo) {
  if (sel.selecting.value) { sel.toggle(photo.id); return }
  modalIndex.value = filteredPhotos.value.findIndex((p) => p.id === photo.id)
  modalPhoto.value = photo
}

function navigate(dir) {
  const next = modalIndex.value + dir
  if (next < 0 || next >= filteredPhotos.value.length) return
  modalIndex.value = next
  modalPhoto.value = filteredPhotos.value[next]
}

async function softDelete(id) {
  await photosApi.delete(id)
  photos.value = photos.value.filter((p) => p.id !== id)
  total.value--
  modalPhoto.value = null
  success('Moved file to Trash')
}

async function deleteAll() {
  const ok = await confirm({
    title: `Move all ${total.value} large files to Trash?`,
    message: 'Favorites are always protected and kept. You can restore items from Trash anytime.',
    confirmText: 'Move to Trash',
    danger: true,
  })
  if (!ok) return
  const { data } = await photosApi.runCleanup({ large: true })
  photos.value = []
  total.value = 0
  totalBytes.value = 0
  sel.clear()
  success(`Moved ${data.deleted} large files to Trash`)
  await load(true)
}

async function bulkDelete() {
  const n = sel.count.value
  await photosApi.bulkDelete(sel.ids.value)
  photos.value = photos.value.filter((p) => !sel.selected.value.has(p.id))
  total.value -= n
  sel.clear()
  success(`Moved ${n} large files to Trash`)
}

async function bulkDownload() {
  try {
    const { data } = await photosApi.downloadZip(sel.ids.value)
    const url = URL.createObjectURL(data)
    const a = document.createElement('a')
    a.href = url
    a.download = 'large-files.zip'
    a.click()
    URL.revokeObjectURL(url)
    success('Downloading large files ZIP')
  } catch {
    toastError('Could not download ZIP')
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

function formatBytes(b) {
  if (!b) return '0 B'
  if (b < 1048576) return `${(b / 1024).toFixed(0)} KB`
  if (b < 1073741824) return `${(b / 1048576).toFixed(1)} MB`
  return `${(b / 1073741824).toFixed(2)} GB`
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
