<template>
  <div>
    <h1 class="text-xl font-bold mb-5">Timeline</h1>

    <div v-if="loading" class="flex justify-center py-20">
      <span class="text-gray-500 animate-pulse">Loading…</span>
    </div>

    <div v-else class="space-y-8">
      <section v-for="group in groups" :key="group.month">
        <h2 class="text-sm font-semibold text-gray-400 uppercase tracking-widest mb-3">
          {{ formatMonth(group.month) }}
          <span class="text-gray-600 font-normal ml-2">{{ group.photos.length }}</span>
        </h2>
        <PhotoGrid :photos="group.photos" @select="selected = $event" />
      </section>

      <div v-if="!groups.length" class="flex flex-col items-center py-20 text-gray-600">
        <span class="text-5xl mb-4">📅</span>
        <p>No dated photos yet — upload some to see a timeline.</p>
      </div>
    </div>

    <PhotoModal v-if="selected" :photo="selected" @close="selected = null" @delete="deletePhoto" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { photosApi } from '../api/photos'
import PhotoGrid from '../components/PhotoGrid.vue'
import PhotoModal from '../components/PhotoModal.vue'

const groups = ref([])
const loading = ref(false)
const selected = ref(null)

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await photosApi.timeline()
    groups.value = data
  } finally {
    loading.value = false
  }
})

function formatMonth(key) {
  if (key === 'unknown') return 'Unknown date'
  const [y, m] = key.split('-')
  return new Date(+y, +m - 1).toLocaleString(undefined, { month: 'long', year: 'numeric' })
}

async function deletePhoto(id) {
  await photosApi.delete(id)
  groups.value = groups.value
    .map((g) => ({ ...g, photos: g.photos.filter((p) => p.id !== id) }))
    .filter((g) => g.photos.length)
  selected.value = null
}
</script>
