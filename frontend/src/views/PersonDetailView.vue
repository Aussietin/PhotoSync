<template>
  <div>
    <div class="flex flex-wrap items-center gap-3 mb-5">
      <router-link to="/people" class="btn-ghost text-sm">← People</router-link>
      <div>
        <h1 class="text-xl font-bold">
          {{ name || 'Unnamed person' }}
          <span class="text-gray-500 font-normal text-base">({{ total }})</span>
        </h1>
        <p class="text-xs text-gray-500 mt-0.5">Photos this person appears in</p>
      </div>
      <div class="ml-auto flex gap-2 flex-wrap">
        <button
          v-if="photos.length"
          class="btn-ghost text-sm text-red-400 hover:text-red-300"
          @click="trashAll"
        >🗑 Trash all photos of this person</button>
      </div>
    </div>

    <PhotoGridSkeleton v-if="loading && !photos.length" :count="18" />

    <template v-else-if="photos.length">
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

    <EmptyState v-else icon="🙂" title="No photos" subtitle="This person has no photos left." />

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
const { success } = useToast()
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
}

async function trashAll() {
  const ok = await confirm({
    title: `Trash all ${total.value} photos of ${name.value || 'this person'}?`,
    message: 'Favorites are kept. Everything goes to Trash and can be restored.',
    confirmText: 'Move to Trash',
    danger: true,
  })
  if (!ok) return
  const { data } = await peopleApi.trashPhotos(id)
  photos.value = []
  total.value = 0
  sel.clear()
  success(`Moved ${data.deleted} photos to Trash`)
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
  const a = document.createElement('a'); a.href = url; a.download = 'person.zip'; a.click()
  URL.revokeObjectURL(url)
}

let observer
onMounted(async () => {
  // Pull the person's name from the list (cheap) for the header.
  try {
    const { data } = await peopleApi.list({ min_photos: 1 })
    name.value = data.people.find((p) => String(p.id) === String(id))?.name || ''
  } catch { /* non-fatal */ }
  await load(true)
  observer = new IntersectionObserver(([entry]) => {
    if (entry.isIntersecting && photos.value.length < total.value && !loading.value) {
      page.value++; load()
    }
  })
  if (sentinel.value) observer.observe(sentinel.value)
})
onBeforeUnmount(() => observer?.disconnect())
</script>
