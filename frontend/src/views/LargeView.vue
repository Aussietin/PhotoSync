<template>
  <div>
    <div class="flex flex-wrap items-center gap-3 mb-5">
      <div>
        <h1 class="text-xl font-bold">
          Large files
          <span class="text-gray-500 font-normal text-base">({{ total }})</span>
        </h1>
        <p class="text-xs text-gray-500 mt-0.5">
          Videos &amp; big photos ≥ {{ thresholdMb }} MB — biggest first.
          <span v-if="totalBytes" class="text-gray-400">{{ formatBytes(totalBytes) }} total.</span>
        </p>
      </div>

      <div class="ml-auto flex gap-2 flex-wrap">
        <button
          v-if="photos.length"
          class="btn-ghost text-sm text-red-400 hover:text-red-300"
          @click="deleteAll"
        >
          🗑 Trash all large files
        </button>
      </div>
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
      icon="🎬"
      title="No large files"
      subtitle="Nothing at or above the size threshold yet. Import or upload some videos and they'll show up here."
    />

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
const totalBytes = ref(0)
const thresholdMb = ref(25)
const page = ref(1)
const loading = ref(false)
const modalPhoto = ref(null)
const modalIndex = ref(-1)
const sentinel = ref(null)
const sel = useSelection()

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
    title: `Move all ${total.value} large files to Trash?`,
    message: 'Favorites are always kept. You can restore from Trash later.',
    confirmText: 'Move to Trash',
    danger: true,
  })
  if (!ok) return
  // Server-side: trashes EVERY large file, not just the ones scrolled into view.
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
  success(`Moved ${n} to Trash`)
}

async function bulkDownload() {
  const { data } = await photosApi.downloadZip(sel.ids.value)
  const url = URL.createObjectURL(data)
  const a = document.createElement('a'); a.href = url; a.download = 'large-files.zip'; a.click()
  URL.revokeObjectURL(url)
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
      page.value++; load()
    }
  })
  if (sentinel.value) observer.observe(sentinel.value)
})
onBeforeUnmount(() => observer?.disconnect())
</script>
