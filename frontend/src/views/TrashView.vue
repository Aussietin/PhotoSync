<template>
  <div>
    <div class="flex items-center justify-between mb-5">
      <h1 class="text-2xl font-bold tracking-tight">Trash <span class="text-gray-500 font-normal text-base">({{ photos.length }})</span></h1>
      <div class="flex gap-2">
        <button v-if="photos.length" class="btn-ghost text-sm" @click="restoreAll">↩️ Restore all</button>
        <button v-if="photos.length" class="btn-danger text-sm" @click="emptyTrash">🗑 Empty trash</button>
      </div>
    </div>

    <div v-if="loading" class="space-y-1">
      <div v-for="i in 6" :key="i" class="card flex items-center gap-3 p-3">
        <Skeleton width="3.5rem" height="3.5rem" rounded="rounded-xl" />
        <div class="flex-1 space-y-2">
          <Skeleton width="50%" height="0.8rem" />
          <Skeleton width="25%" height="0.65rem" />
        </div>
      </div>
    </div>

    <div v-else-if="photos.length" class="space-y-1">
      <div
        v-for="photo in photos"
        :key="photo.id"
        class="card flex items-center gap-3 p-3"
      >
        <img
          v-if="photo.thumbnail_url"
          :src="photo.thumbnail_url"
          class="w-14 h-14 object-cover rounded-xl flex-shrink-0"
        />
        <div class="flex-1 min-w-0">
          <p class="text-sm truncate text-gray-300">{{ photo.filename }}</p>
          <p class="text-xs text-gray-500 mt-0.5">Deleted {{ formatRelative(photo.deleted_at) }}</p>
        </div>
        <div class="flex gap-2 flex-shrink-0">
          <button class="btn-ghost text-xs" @click="restore(photo.id)">Restore</button>
          <button class="btn-ghost text-xs text-red-400 hover:text-red-300" @click="permanentDelete(photo.id)">Delete forever</button>
        </div>
      </div>
    </div>

    <EmptyState
      v-else
      icon="🗑️"
      title="Trash is empty"
      subtitle="Deleted photos land here first, so you can always restore them."
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { photosApi } from '../api/photos'
import Skeleton from '../components/ui/Skeleton.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import { useToast } from '../composables/useToast'
import { useConfirm } from '../composables/useConfirm'

const { success } = useToast()
const { confirm } = useConfirm()

const photos = ref([])
const loading = ref(false)

onMounted(load)

async function load() {
  loading.value = true
  try {
    const { data } = await photosApi.trash()
    photos.value = data.photos
  } finally {
    loading.value = false
  }
}

async function restore(id) {
  await photosApi.restore(id)
  photos.value = photos.value.filter((p) => p.id !== id)
  success('Photo restored')
}

async function permanentDelete(id) {
  const ok = await confirm({
    title: 'Delete forever?',
    message: 'This photo will be permanently removed. This cannot be undone.',
    confirmText: 'Delete forever',
    danger: true,
  })
  if (!ok) return
  await photosApi.permanentDelete(id)
  photos.value = photos.value.filter((p) => p.id !== id)
  success('Photo permanently deleted')
}

async function restoreAll() {
  const n = photos.value.length
  await photosApi.bulkRestore(photos.value.map((p) => p.id))
  photos.value = []
  success(`Restored ${n} photo${n > 1 ? 's' : ''}`)
}

async function emptyTrash() {
  const n = photos.value.length
  const ok = await confirm({
    title: `Permanently delete ${n} photo${n > 1 ? 's' : ''}?`,
    message: 'Everything in Trash will be gone for good. This cannot be undone.',
    confirmText: 'Empty trash',
    danger: true,
  })
  if (!ok) return
  // Server-side: removes files + rows for everything in trash, not just loaded.
  await photosApi.emptyTrash()
  photos.value = []
  success('Trash emptied')
}

function formatRelative(iso) {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}
</script>
