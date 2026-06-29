<template>
  <div>
    <div class="flex items-center gap-3 mb-5">
      <router-link to="/albums" class="text-gray-500 hover:text-gray-300 text-lg">←</router-link>
      <div class="flex-1 min-w-0">
        <h1 class="text-xl font-bold truncate">{{ album?.name }}</h1>
        <p v-if="album?.description" class="text-sm text-gray-500 truncate">{{ album.description }}</p>
      </div>
      <button class="btn-danger text-sm" @click="deleteAlbum">🗑 Delete album</button>
    </div>

    <PhotoGridSkeleton v-if="loading" :count="18" />

    <PhotoGrid
      v-else
      :photos="photos"
      :selection="sel"
      :selection-mode="sel.selecting.value"
      :show-upload-hint="false"
      @select="openModal"
      @toggle-favorite="toggleFavorite"
    />

    <PhotoModal
      v-if="modalPhoto"
      :photo="modalPhoto"
      :has-prev="modalIndex > 0"
      :has-next="modalIndex < photos.length - 1"
      @close="modalPhoto = null"
      @delete="removeFromAlbum"
      @toggle-favorite="toggleFavorite"
      @update-notes="updateNotes"
      @prev="navigate(-1)"
      @next="navigate(1)"
    />

    <BatchToolbar
      :count="sel.count.value"
      @favorite="bulkFavorite"
      @download="bulkDownload"
      @delete="bulkRemove"
      @clear="sel.clear()"
    >
      <template #extra>
        <button class="toolbar-btn" @click="bulkRemove">Remove from album</button>
      </template>
    </BatchToolbar>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { albumsApi, photosApi } from '../api/photos'
import { useSelection } from '../composables/useSelection'
import PhotoGrid from '../components/PhotoGrid.vue'
import PhotoGridSkeleton from '../components/ui/PhotoGridSkeleton.vue'
import PhotoModal from '../components/PhotoModal.vue'
import BatchToolbar from '../components/BatchToolbar.vue'
import { useToast } from '../composables/useToast'
import { useConfirm } from '../composables/useConfirm'

const { success } = useToast()
const { confirm } = useConfirm()

const route = useRoute()
const router = useRouter()
const album = ref(null)
const photos = ref([])
const loading = ref(false)
const modalPhoto = ref(null)
const modalIndex = ref(-1)
const sel = useSelection()

onMounted(load)

async function load() {
  loading.value = true
  try {
    const { data } = await albumsApi.get(route.params.id)
    album.value = data
    photos.value = data.photos
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

async function removeFromAlbum(photoId) {
  await albumsApi.removePhoto(route.params.id, photoId)
  photos.value = photos.value.filter((p) => p.id !== photoId)
  modalPhoto.value = null
}

async function toggleFavorite(id) {
  const { data } = await photosApi.toggleFavorite(id)
  const photo = photos.value.find((p) => p.id === id)
  if (photo) photo.is_favorite = data.is_favorite
  if (modalPhoto.value?.id === id) modalPhoto.value = { ...modalPhoto.value, is_favorite: data.is_favorite }
}

async function updateNotes(id, notes) {
  await photosApi.updateNotes(id, notes)
  const photo = photos.value.find((p) => p.id === id)
  if (photo) photo.notes = notes
}

async function deleteAlbum() {
  const ok = await confirm({
    title: `Delete “${album.value?.name}”?`,
    message: 'The album is removed, but your photos stay in the library.',
    confirmText: 'Delete album',
    danger: true,
  })
  if (!ok) return
  await albumsApi.delete(route.params.id)
  success('Album deleted')
  router.push('/albums')
}

async function bulkFavorite() {
  await photosApi.bulkFavorite(sel.ids.value)
  photos.value.forEach((p) => { if (sel.selected.value.has(p.id)) p.is_favorite = true })
  sel.clear()
}

async function bulkRemove() {
  await Promise.all(sel.ids.value.map((id) => albumsApi.removePhoto(route.params.id, id)))
  photos.value = photos.value.filter((p) => !sel.selected.value.has(p.id))
  sel.clear()
}

async function bulkDownload() {
  const { data } = await photosApi.downloadZip(sel.ids.value)
  const url = URL.createObjectURL(data)
  const a = document.createElement('a')
  a.href = url; a.download = `${album.value?.name ?? 'album'}.zip`; a.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.toolbar-btn {
  @apply flex items-center gap-1 px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 text-gray-200 text-sm font-medium transition-colors whitespace-nowrap;
}
</style>
