<template>
  <div class="space-y-4">
    <!-- Header Banner -->
    <div class="flex flex-wrap items-center justify-between gap-3 bg-ink-900/60 p-4 rounded-2xl border border-white/5 backdrop-blur-md">
      <div class="flex items-center gap-3">
        <router-link to="/people" class="btn-ghost text-xs py-1.5 px-3">← Back to People</router-link>
        <div>
          <h1 class="text-xl font-extrabold tracking-tight text-white flex items-center gap-2">
            <span>{{ name || 'Unnamed Person' }}</span>
            <span class="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-brand-500/20 text-brand-300 border border-brand-400/20">
              {{ total.toLocaleString() }} photos
            </span>
          </h1>
          <p class="text-xs text-gray-400 mt-0.5">All pictures containing this face.</p>
        </div>
      </div>

      <div class="flex items-center gap-2 flex-wrap ml-auto">
        <button
          v-if="photos.length"
          class="btn-danger text-xs sm:text-sm py-2 px-4 shadow-sm"
          @click="trashAll"
        >
          🗑 Trash All Photos of This Person
        </button>
      </div>
    </div>

    <PhotoGridSkeleton v-if="loading && !photos.length" :count="18" />

    <template v-else-if="photos.length">
      <!-- Batch controls -->
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
      icon="🙂"
      title="No photos for this person"
      subtitle="All photos of this person have been moved to Trash or removed."
    >
      <template #action>
        <router-link to="/people" class="btn-ghost text-sm">← Return to People</router-link>
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
import { useRoute } from 'vue-router'
import { peopleApi, photosApi } from '../api/photos'
import { useSelection } from '../composables/useSelection'
import PhotoGrid from '../components/PhotoGrid.vue'
import PhotoGridSkeleton from '../components/ui/PhotoGridSkeleton.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import PhotoModal from '../components/PhotoModal.vue'
import BatchToolbar from '../components/BatchToolbar.vue'
import { useToast } from '../composables/useToast'
import { useConfirm } from '../composables/useConfirm'

const route = useRoute()
const id = route.params.id
const { success, error: toastError } = useToast()
const { confirm } = useConfirm()

const photos = ref([])
const total = ref(0)
const name = ref('')
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
    const { data } = await peopleApi.photos(id, { page: page.value, per_page: 50 })
    if (reset) photos.value = data.photos
    else photos.value.push(...data.photos)
    total.value = data.total
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

async function softDelete(pid) {
  await photosApi.delete(pid)
  photos.value = photos.value.filter((p) => p.id !== pid)
  total.value--
  modalPhoto.value = null
  success('Moved photo to Trash')
}

async function trashAll() {
  const ok = await confirm({
    title: `Trash all ${total.value} photos of ${name.value || 'this person'}?`,
    message: 'Favorites are kept, and photos where a known contact also appears will be automatically skipped.',
    confirmText: 'Move to Trash',
    danger: true,
  })
  if (!ok) return
  const { data } = await peopleApi.trashPhotos(id)
  sel.clear()
  if (data.skipped_mixed) {
    success(`Moved ${data.deleted} to Trash — skipped ${data.skipped_mixed} group photos with known contacts`)
  } else {
    success(`Moved ${data.deleted} photos to Trash`)
  }
  page.value = 1
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
  try {
    const { data } = await photosApi.downloadZip(sel.ids.value)
    const url = URL.createObjectURL(data)
    const a = document.createElement('a')
    a.href = url
    a.download = `${name.value || 'person'}-photos.zip`
    a.click()
    URL.revokeObjectURL(url)
    success('Downloading ZIP export')
  } catch {
    toastError('Could not download ZIP')
  }
}

async function toggleFavorite(pid) {
  const { data } = await photosApi.toggleFavorite(pid)
  const photo = photos.value.find((p) => p.id === pid)
  if (photo) photo.is_favorite = data.is_favorite
  if (modalPhoto.value?.id === pid) modalPhoto.value = { ...modalPhoto.value, is_favorite: data.is_favorite }
}

async function bulkFavorite() {
  const n = sel.count.value
  await photosApi.bulkFavorite(sel.ids.value)
  photos.value.forEach((p) => { if (sel.selected.value.has(p.id)) p.is_favorite = true })
  sel.clear()
  success(`Added ${n} to Favorites (protected from cleanup)`)
}

let observer
onMounted(async () => {
  try {
    const { data } = await peopleApi.list({ min_photos: 1 })
    name.value = data.people.find((p) => String(p.id) === String(id))?.name || ''
  } catch { /* non-fatal */ }
  await load(true)
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
