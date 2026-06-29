<template>
  <div>
    <h1 class="text-2xl font-bold tracking-tight mb-5">Timeline</h1>

    <div v-if="loading" class="space-y-8">
      <section v-for="i in 2" :key="i">
        <Skeleton width="8rem" height="0.8rem" class="mb-3" />
        <PhotoGridSkeleton :count="12" />
      </section>
    </div>

    <div v-else class="space-y-8">
      <section v-for="group in groups" :key="group.month">
        <h2 class="text-sm font-semibold text-gray-400 uppercase tracking-widest mb-3">
          {{ formatMonth(group.month) }}
          <span class="text-gray-600 font-normal ml-2">{{ group.photos.length }}</span>
        </h2>
        <PhotoGrid :photos="group.photos" @select="selected = $event" />
      </section>

      <EmptyState
        v-if="!groups.length"
        icon="📅"
        title="No dated photos yet"
        subtitle="Upload photos with date info to see them organised into a timeline."
      >
        <template #action>
          <router-link to="/upload" class="btn-primary text-sm">⬆️ Upload photos</router-link>
        </template>
      </EmptyState>
    </div>

    <PhotoModal v-if="selected" :photo="selected" @close="selected = null" @delete="deletePhoto" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { photosApi } from '../api/photos'
import PhotoGrid from '../components/PhotoGrid.vue'
import PhotoGridSkeleton from '../components/ui/PhotoGridSkeleton.vue'
import Skeleton from '../components/ui/Skeleton.vue'
import EmptyState from '../components/ui/EmptyState.vue'
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
