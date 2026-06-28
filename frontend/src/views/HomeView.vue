<template>
  <div>
    <!-- Controls bar -->
    <div class="flex flex-wrap items-center gap-2 mb-4">
      <h1 class="text-xl font-bold mr-auto">
        Library
        <span class="text-gray-500 font-normal text-base">({{ total }})</span>
      </h1>

      <!-- Favorites filter -->
      <button
        class="px-3 py-1.5 rounded-xl text-sm font-medium transition-colors"
        :class="favoritesOnly ? 'bg-red-500/20 text-red-400' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'"
        @click="toggleFavorites"
      >♥ Favorites</button>

      <!-- Sort -->
      <select
        v-model="sort"
        class="bg-gray-800 border border-gray-700 rounded-xl px-3 py-1.5 text-sm text-gray-300 focus:outline-none focus:border-brand-500"
        @change="reload"
      >
        <option value="date_desc">Newest first</option>
        <option value="date_asc">Oldest first</option>
        <option value="quality_desc">Best quality</option>
        <option value="size_desc">Largest files</option>
        <option value="size_asc">Smallest files</option>
        <option value="name_asc">Name A–Z</option>
        <option value="created_desc">Recently added</option>
      </select>

      <!-- Select mode toggle -->
      <button
        class="px-3 py-1.5 rounded-xl text-sm font-medium transition-colors"
        :class="sel.selecting.value ? 'bg-brand-500 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'"
        @click="sel.selecting.value ? sel.clear() : (sel.selecting.value = true)"
      >Select</button>

      <!-- Select all -->
      <button
        v-if="sel.selecting.value"
        class="px-3 py-1.5 rounded-xl bg-gray-800 text-gray-400 hover:bg-gray-700 text-sm"
        @click="sel.selectAll(photos.map(p => p.id))"
      >All</button>
    </div>

    <div v-if="loading && !photos.length" class="flex justify-center py-20">
      <span class="text-gray-500 animate-pulse">Loading…</span>
    </div>

    <PhotoGrid
      :photos="photos"
      :selection="sel"
      :selection-mode="sel.selecting.value"
      @select="openModal"
      @toggle-favorite="toggleFavorite"
    />

    <div ref="sentinel" class="h-10" />

    <!-- Photo modal -->
    <PhotoModal
      v-if="modalPhoto"
      :photo="modalPhoto"
      :has-prev="modalIndex > 0"
      :has-next="modalIndex < photos.length - 1"
      @close="modalPhoto = null"
      @delete="softDelete"
      @toggle-favorite="toggleFavorite"
      @update-notes="updateNotes"
      @prev="navigate(-1)"
      @next="navigate(1)"
    />

    <!-- Batch toolbar -->
    <BatchToolbar
      :count="sel.count.value"
      @favorite="bulkFavorite"
      @download="bulkDownload"
      @delete="bulkDelete"
      @clear="sel.clear()"
    />
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { photosApi } from '../api/photos'
import { useSelection } from '../composables/useSelection'
import PhotoGrid from '../components/PhotoGrid.vue'
import PhotoModal from '../components/PhotoModal.vue'
import BatchToolbar from '../components/BatchToolbar.vue'

const photos = ref([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const sort = ref('date_desc')
const favoritesOnly = ref(false)
const modalPhoto = ref(null)
const modalIndex = ref(-1)
const sentinel = ref(null)
const sel = useSelection()

async function load(reset = false) {
  if (loading.value) return
  loading.value = true
  try {
    const { data } = await photosApi.list({
      page: page.value, per_page: 50,
      include_duplicates: false,
      favorites_only: favoritesOnly.value,
      sort: sort.value,
    })
    if (reset) photos.value = data.photos
    else photos.value.push(...data.photos)
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function reload() { page.value = 1; sel.clear(); load(true) }
function toggleFavorites() { favoritesOnly.value = !favoritesOnly.value; reload() }

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

async function bulkDelete() {
  if (!sel.count.value) return
  await photosApi.bulkDelete(sel.ids.value)
  photos.value = photos.value.filter((p) => !sel.selected.value.has(p.id))
  total.value -= sel.count.value
  sel.clear()
}

async function bulkFavorite() {
  if (!sel.count.value) return
  await photosApi.bulkFavorite(sel.ids.value)
  photos.value.forEach((p) => { if (sel.selected.value.has(p.id)) p.is_favorite = true })
  sel.clear()
}

async function bulkDownload() {
  if (!sel.count.value) return
  const { data } = await photosApi.downloadZip(sel.ids.value)
  const url = URL.createObjectURL(data)
  const a = document.createElement('a')
  a.href = url
  a.download = 'photosync-export.zip'
  a.click()
  URL.revokeObjectURL(url)
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
