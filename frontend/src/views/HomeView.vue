<template>
  <div class="space-y-4">
    <OnboardingBanner />

    <!-- Controls & Filter bar -->
    <div class="flex flex-wrap items-center justify-between gap-3 bg-ink-900/60 p-3 rounded-2xl border border-white/5 backdrop-blur-md">
      <div class="flex items-center gap-3">
        <h1 class="text-xl font-extrabold tracking-tight text-white flex items-center gap-2">
          <span>Library</span>
          <span class="text-xs font-semibold px-2 py-0.5 rounded-full bg-brand-500/20 text-brand-300 border border-brand-400/20 font-mono">
            {{ total.toLocaleString() }}
          </span>
        </h1>

        <!-- Quick filter chips -->
        <div class="hidden sm:flex items-center gap-1.5 pl-2 border-l border-white/10">
          <button
            class="chip"
            :class="!favoritesOnly && !videosOnly ? 'chip-active' : 'chip-muted'"
            @click="setFilter('all')"
          >All</button>
          <button
            class="chip"
            :class="favoritesOnly ? 'chip-active text-red-300 border-red-500/40 bg-red-500/20' : 'chip-muted'"
            @click="setFilter('favorites')"
          >♥ Favorites</button>
          <button
            class="chip"
            :class="videosOnly ? 'chip-active text-sky-300 border-sky-500/40 bg-sky-500/20' : 'chip-muted'"
            @click="setFilter('videos')"
          >🎬 Videos</button>
        </div>
      </div>

      <div class="flex items-center gap-2 flex-wrap ml-auto">
        <!-- Sort Dropdown -->
        <div class="relative">
          <select
            v-model="sort"
            class="bg-ink-850 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-brand-400/60 transition-colors cursor-pointer"
            @change="reload"
          >
            <option value="date_desc">📅 Newest first</option>
            <option value="date_asc">📅 Oldest first</option>
            <option value="quality_desc">⭐ Best quality</option>
            <option value="size_desc">💾 Largest files</option>
            <option value="size_asc">💾 Smallest files</option>
            <option value="name_asc">🔤 Name A–Z</option>
            <option value="created_desc">⏱ Recently added</option>
          </select>
        </div>

        <!-- Select Mode Toggle -->
        <button
          class="btn-ghost text-xs py-1.5 px-3"
          :class="sel.selecting.value && 'bg-brand-500/20 border-brand-400/40 text-brand-200'"
          @click="sel.selecting.value ? sel.clear() : (sel.selecting.value = true)"
        >
          {{ sel.selecting.value ? 'Cancel' : 'Select' }}
        </button>

        <!-- Select All in Mode -->
        <button
          v-if="sel.selecting.value"
          class="btn-ghost text-xs py-1.5 px-3"
          @click="sel.selectAll(photos.map(p => p.id))"
        >
          All ({{ photos.length }})
        </button>
      </div>
    </div>

    <!-- Mobile filter chips -->
    <div class="flex sm:hidden items-center gap-1.5 overflow-x-auto no-scrollbar pb-1">
      <button
        class="chip"
        :class="!favoritesOnly && !videosOnly ? 'chip-active' : 'chip-muted'"
        @click="setFilter('all')"
      >All</button>
      <button
        class="chip"
        :class="favoritesOnly ? 'chip-active text-red-300 border-red-500/40 bg-red-500/20' : 'chip-muted'"
        @click="setFilter('favorites')"
      >♥ Favorites</button>
      <button
        class="chip"
        :class="videosOnly ? 'chip-active text-sky-300 border-sky-500/40 bg-sky-500/20' : 'chip-muted'"
        @click="setFilter('videos')"
      >🎬 Videos</button>
    </div>

    <PhotoGridSkeleton v-if="loading && !photos.length" :count="24" />

    <EmptyState
      v-else-if="!photos.length"
      icon="📷"
      title="No photos to display"
      :subtitle="favoritesOnly ? 'You haven’t favorited any photos yet.' : videosOnly ? 'No videos found in your library.' : 'Upload a batch from your phone or import a folder to get started.'"
    >
      <template #action>
        <div v-if="!favoritesOnly && !videosOnly" class="flex gap-2 justify-center">
          <router-link to="/upload" class="btn-primary text-sm">⬆ Upload from phone</router-link>
          <router-link to="/import" class="btn-ghost text-sm">📥 Import a folder</router-link>
        </div>
        <button v-else class="btn-ghost text-sm" @click="setFilter('all')">View all photos</button>
      </template>
    </EmptyState>

    <PhotoGrid
      v-else
      :photos="filteredPhotos"
      :selection="sel"
      :selection-mode="sel.selecting.value"
      @select="openModal"
      @toggle-favorite="toggleFavorite"
    />

    <!-- Infinite-scroll loading footer -->
    <div v-if="loading && photos.length" class="flex justify-center py-6">
      <Spinner :size="22" label="Loading more photos…" />
    </div>

    <div ref="sentinel" class="h-10" />

    <!-- Photo modal -->
    <PhotoModal
      v-if="modalPhoto"
      :photo="modalPhoto"
      :has-prev="modalIndex > 0"
      :has-next="modalIndex < filteredPhotos.length - 1"
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
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { photosApi } from '../api/photos'
import { useSelection } from '../composables/useSelection'
import PhotoGrid from '../components/PhotoGrid.vue'
import PhotoGridSkeleton from '../components/ui/PhotoGridSkeleton.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import Spinner from '../components/ui/Spinner.vue'
import PhotoModal from '../components/PhotoModal.vue'
import BatchToolbar from '../components/BatchToolbar.vue'
import OnboardingBanner from '../components/OnboardingBanner.vue'
import { useToast } from '../composables/useToast'
import { useConfirm } from '../composables/useConfirm'

const { success, error: toastError } = useToast()
const { confirm } = useConfirm()

const photos = ref([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const sort = ref('date_desc')
const favoritesOnly = ref(false)
const videosOnly = ref(false)
const modalPhoto = ref(null)
const modalIndex = ref(-1)
const sentinel = ref(null)
const sel = useSelection()

const filteredPhotos = computed(() => {
  if (videosOnly.value) {
    return photos.value.filter((p) => p.is_video)
  }
  return photos.value
})

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

function reload() {
  page.value = 1
  sel.clear()
  load(true)
}

function setFilter(type) {
  if (type === 'favorites') {
    favoritesOnly.value = true
    videosOnly.value = false
  } else if (type === 'videos') {
    favoritesOnly.value = false
    videosOnly.value = true
  } else {
    favoritesOnly.value = false
    videosOnly.value = false
  }
  reload()
}

function openModal(photo) {
  if (sel.selecting.value) {
    sel.toggle(photo.id)
    return
  }
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
  success('Moved photo to Trash')
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
  const n = sel.count.value
  const ok = await confirm({
    title: `Move ${n} photo${n > 1 ? 's' : ''} to Trash?`,
    message: 'You can restore them from Trash later.',
    confirmText: 'Move to Trash',
    danger: true,
  })
  if (!ok) return
  await photosApi.bulkDelete(sel.ids.value)
  photos.value = photos.value.filter((p) => !sel.selected.value.has(p.id))
  total.value -= n
  sel.clear()
  success(`Moved ${n} photo${n > 1 ? 's' : ''} to Trash`)
}

async function bulkFavorite() {
  if (!sel.count.value) return
  const n = sel.count.value
  await photosApi.bulkFavorite(sel.ids.value)
  photos.value.forEach((p) => { if (sel.selected.value.has(p.id)) p.is_favorite = true })
  sel.clear()
  success(`Added ${n} to Favorites`)
}

async function bulkDownload() {
  if (!sel.count.value) return
  try {
    const { data } = await photosApi.downloadZip(sel.ids.value)
    const url = URL.createObjectURL(data)
    const a = document.createElement('a')
    a.href = url
    a.download = 'photosync-export.zip'
    a.click()
    URL.revokeObjectURL(url)
    success('Your ZIP is downloading')
  } catch {
    toastError('Could not build the ZIP — please try again.')
  }
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
