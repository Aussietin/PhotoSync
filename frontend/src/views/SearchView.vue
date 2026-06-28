<template>
  <div>
    <h1 class="text-xl font-bold mb-4">Search</h1>

    <div class="space-y-3 mb-6">
      <SearchBar v-model="query" placeholder="Search by tag, filename…" @search="doSearch" />

      <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <input v-model="dateFrom" type="date" class="input-field" placeholder="From date" />
        <input v-model="dateTo" type="date" class="input-field" placeholder="To date" />
        <input v-model="camera" class="input-field" placeholder="Camera model" />
        <button class="btn-primary text-sm" @click="doSearch">Search</button>
      </div>

      <!-- Tag chips -->
      <div v-if="allTags.length" class="flex flex-wrap gap-1.5">
        <button
          v-for="tag in allTags"
          :key="tag"
          class="px-2 py-0.5 rounded-full text-xs transition-colors"
          :class="activeTag === tag ? 'bg-brand-500 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'"
          @click="toggleTag(tag)"
        >{{ tag }}</button>
      </div>
    </div>

    <div v-if="loading" class="flex justify-center py-10">
      <span class="text-gray-500 animate-pulse">Searching…</span>
    </div>

    <div v-else-if="searched">
      <p class="text-sm text-gray-500 mb-3">{{ results.length }} result{{ results.length !== 1 ? 's' : '' }}</p>
      <PhotoGrid :photos="results" @select="selected = $event" />
    </div>

    <PhotoModal v-if="selected" :photo="selected" @close="selected = null" @delete="deletePhoto" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { searchApi, tagsApi, photosApi } from '../api/photos'
import SearchBar from '../components/SearchBar.vue'
import PhotoGrid from '../components/PhotoGrid.vue'
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

<style scoped>
.input-field {
  @apply bg-gray-800 border border-gray-700 rounded-xl px-3 py-2 text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-brand-500 w-full;
}
</style>
