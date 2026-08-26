<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3 bg-ink-900/60 p-4 rounded-2xl border border-white/5 backdrop-blur-md">
      <div>
        <h1 class="text-xl font-extrabold tracking-tight text-white flex items-center gap-2">
          <span>Chronological Timeline</span>
        </h1>
        <p class="text-xs text-gray-400 mt-1">
          Explore your media history organized by month and capture date.
        </p>
      </div>
    </div>

    <div v-if="loading" class="space-y-8">
      <section v-for="i in 2" :key="i" class="space-y-3">
        <Skeleton width="10rem" height="1rem" />
        <PhotoGridSkeleton :count="12" />
      </section>
    </div>

    <div v-else class="space-y-8">
      <section v-for="group in groups" :key="group.month" class="space-y-3">
        <div class="flex items-center gap-2 border-b border-white/5 pb-2">
          <span class="w-2 h-2 rounded-full bg-brand-400" />
          <h2 class="text-sm font-bold text-gray-200 tracking-wide">
            {{ formatMonth(group.month) }}
          </h2>
          <span class="text-xs font-mono font-semibold px-2 py-0.5 rounded-full bg-white/5 text-gray-400 border border-white/5">
            {{ group.photos.length }}
          </span>
        </div>
        <PhotoGrid :photos="group.photos" @select="selected = $event" @toggle-favorite="toggleFavorite" />
      </section>

      <EmptyState
        v-if="!groups.length"
        icon="📅"
        title="No dated photos found"
        subtitle="Import or upload photos with EXIF capture dates to view your timeline."
      >
        <template #action>
          <router-link to="/upload" class="btn-primary text-sm">⬆️ Upload Photos</router-link>
        </template>
      </EmptyState>
    </div>

    <PhotoModal
      v-if="selected"
      :photo="selected"
      @close="selected = null"
      @delete="deletePhoto"
      @toggle-favorite="toggleFavorite"
    />
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
import { useToast } from '../composables/useToast'

const { success } = useToast()

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
  if (key === 'unknown') return 'Undated & Scanned'
  const [y, m] = key.split('-')
  return new Date(+y, +m - 1).toLocaleString(undefined, { month: 'long', year: 'numeric' })
}

async function deletePhoto(id) {
  await photosApi.delete(id)
  groups.value = groups.value
    .map((g) => ({ ...g, photos: g.photos.filter((p) => p.id !== id) }))
    .filter((g) => g.photos.length)
  selected.value = null
  success('Moved photo to Trash')
}

async function toggleFavorite(id) {
  const { data } = await photosApi.toggleFavorite(id)
  for (const g of groups.value) {
    const photo = g.photos.find((p) => p.id === id)
    if (photo) { photo.is_favorite = data.is_favorite; break }
  }
  if (selected.value?.id === id) selected.value = { ...selected.value, is_favorite: data.is_favorite }
}
</script>
