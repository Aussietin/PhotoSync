<template>
  <div>
    <h1 class="text-2xl font-bold tracking-tight mb-4">Search</h1>

    <div class="space-y-3 mb-6">
      <SearchBar v-model="query" placeholder="Search by tag, filename…" @search="doSearch" />

      <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <input v-model="dateFrom" type="date" class="input" placeholder="From date" />
        <input v-model="dateTo" type="date" class="input" placeholder="To date" />
        <input v-model="camera" class="input" placeholder="Camera model" />
        <button class="btn-primary text-sm" @click="doSearch">🔍 Search</button>
      </div>

      <!-- Tag chips -->
      <div v-if="allTags.length" class="flex flex-wrap gap-1.5">
        <button
          v-for="tag in allTags"
          :key="tag"
          class="text-xs"
          :class="activeTag === tag ? 'chip-active' : 'chip-muted'"
          @click="toggleTag(tag)"
        >{{ tag }}</button>
      </div>
    </div>

    <PhotoGridSkeleton v-if="loading" :count="12" />

    <div v-else-if="searched && results.length">
      <p class="text-sm text-gray-500 mb-3">{{ results.length }} result{{ results.length !== 1 ? 's' : '' }}</p>
      <PhotoGrid :photos="results" @select="selected = $event" />
    </div>

    <EmptyState
      v-else-if="searched"
      icon="🔍"
      title="No matches found"
      subtitle="Try a different keyword, tag, or widen your date range."
    />

    <EmptyState
      v-else
      icon="🔎"
      title="Search your library"
      subtitle="Find photos by tag, filename, camera, or date taken."
    />

    <PhotoModal v-if="selected" :photo="selected" @close="selected = null" @delete="deletePhoto" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { searchApi, tagsApi, photosApi } from '../api/photos'
import SearchBar from '../components/SearchBar.vue'
import PhotoGrid from '../components/PhotoGrid.vue'
import PhotoGridSkeleton from '../components/ui/PhotoGridSkeleton.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import PhotoModal from '../components/PhotoModal.vue'

const query = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const camera = ref('')
const activeTag = ref(null)
const allTags = ref([])
const results = ref([])
const loading = ref(false)
const searched = ref(false)
const selected = ref(null)

onMounted(async () => {
  const { data } = await tagsApi.list()
  allTags.value = data.tags
})

function toggleTag(tag) {
  activeTag.value = activeTag.value === tag ? null : tag
  doSearch()
}

async function doSearch() {
  loading.value = true
  searched.value = true
  try {
    const params = {}
    if (query.value) params.q = query.value
    if (activeTag.value) params.tag = activeTag.value
    if (dateFrom.value) params.date_from = dateFrom.value
    if (dateTo.value) params.date_to = dateTo.value
    if (camera.value) params.camera = camera.value
    const { data } = await searchApi.search(params)
    results.value = data.photos
  } finally {
    loading.value = false
  }
}

async function deletePhoto(id) {
  await photosApi.delete(id)
  results.value = results.value.filter((p) => p.id !== id)
  selected.value = null
}
</script>
