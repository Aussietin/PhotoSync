<template>
  <div>
    <div class="flex items-center justify-between mb-5">
      <h1 class="text-xl font-bold">Trash <span class="text-gray-500 font-normal text-base">({{ photos.length }})</span></h1>
      <div class="flex gap-2">
        <button v-if="photos.length" class="btn-ghost text-sm" @click="restoreAll">Restore all</button>
        <button v-if="photos.length" class="btn-ghost text-sm text-red-400 hover:text-red-300" @click="emptyTrash">Empty trash</button>
      </div>
    </div>

    <div v-if="loading" class="flex justify-center py-20">
      <span class="text-gray-500 animate-pulse">Loading…</span>
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

    <div v-else class="flex flex-col items-center py-20 text-gray-600">
      <span class="text-5xl mb-4">🗑</span>
      <p>Trash is empty.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { photosApi } from '../api/photos'

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
}

async function permanentDelete(id) {
  if (!confirm('Permanently delete this photo? This cannot be undone.')) return
  await photosApi.permanentDelete(id)
  photos.value = photos.value.filter((p) => p.id !== id)
}

async function restoreAll() {
  await photosApi.bulkRestore(photos.value.map((p) => p.id))
  photos.value = []
}

async function emptyTrash() {
  if (!confirm(`Permanently delete all ${photos.value.length} photos? This cannot be undone.`)) return
  // Server-side: removes files + rows for everything in trash, not just loaded.
  await photosApi.emptyTrash()
  photos.value = []
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
