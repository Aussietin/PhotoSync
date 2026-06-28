<template>
  <div>
    <div class="flex items-center justify-between mb-5">
      <h1 class="text-xl font-bold">Duplicates <span class="text-gray-500 font-normal text-base">({{ duplicates.length }})</span></h1>
      <button
        v-if="duplicates.length"
        class="btn-ghost text-sm text-red-400 hover:text-red-300"
        @click="deleteAll"
      >
        Delete all duplicates
      </button>
    </div>

    <div v-if="loading" class="flex justify-center py-20">
      <span class="text-gray-500 animate-pulse">Loading…</span>
    </div>

    <div v-else-if="duplicates.length" class="space-y-1">
      <div
        v-for="photo in duplicates"
        :key="photo.id"
        class="card flex items-center gap-3 p-3"
      >
        <img
          v-if="photo.thumbnail_url"
          :src="photo.thumbnail_url"
          class="w-16 h-16 object-cover rounded-xl flex-shrink-0"
        />
        <div class="flex-1 min-w-0">
          <p class="text-sm truncate text-gray-300">{{ photo.filename }}</p>
          <p class="text-xs text-gray-500 mt-0.5">Duplicate of photo #{{ photo.duplicate_of_id }}</p>
        </div>
        <button
          class="btn-ghost text-red-400 hover:text-red-300 text-sm flex-shrink-0"
          @click="deleteOne(photo.id)"
        >Delete</button>
      </div>
    </div>

    <div v-else class="flex flex-col items-center py-20 text-gray-600">
      <span class="text-5xl mb-4">✅</span>
      <p>No duplicates found — your library is clean!</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { photosApi } from '../api/photos'

const duplicates = ref([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await photosApi.duplicates()
    duplicates.value = data.duplicates
  } finally {
    loading.value = false
  }
})

async function deleteOne(id) {
  await photosApi.delete(id)
  duplicates.value = duplicates.value.filter((p) => p.id !== id)
}

async function deleteAll() {
  if (!confirm(`Delete all ${duplicates.value.length} duplicates?`)) return
  await Promise.all(duplicates.value.map((p) => photosApi.delete(p.id)))
  duplicates.value = []
}
</script>
