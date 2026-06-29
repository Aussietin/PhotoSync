<template>
  <div>
    <h1 class="text-xl font-bold mb-4">Search</h1>

    <!-- Mode toggle: keyword (exact) vs smart (meaning-based, local CLIP) -->
    <div class="flex gap-1 mb-4 bg-gray-800 p-1 rounded-xl w-fit">
      <button
        class="px-3 py-1 rounded-lg text-sm transition-colors"
        :class="mode === 'keyword' ? 'bg-brand-500 text-white' : 'text-gray-400 hover:text-gray-200'"
        @click="setMode('keyword')"
      >Keyword</button>
      <button
        class="px-3 py-1 rounded-lg text-sm transition-colors"
        :class="mode === 'smart' ? 'bg-brand-500 text-white' : 'text-gray-400 hover:text-gray-200'"
        @click="setMode('smart')"
      >✨ Smart</button>
    </div>

    <div class="space-y-3 mb-6">
      <SearchBar
        v-model="query"
        :placeholder="mode === 'smart' ? 'Describe it: “dog at the beach”, “receipts”…' : 'Search by tag, filename…'"
        @search="doSearch"
      />

      <p v-if="mode === 'smart'" class="text-xs text-gray-500">
        Smart search runs a local AI model on your machine — nothing is uploaded. Filters below apply to keyword search only.
      </p>

      <div v-if="mode === 'keyword'" class="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <input v-model="dateFrom" type="date" class="input-field" placeholder="From date" />
        <input v-model="dateTo" type="date" class="input-field" placeholder="To date" />
        <input v-model="camera" class="input-field" placeholder="Camera model" />
        <button class="btn-primary text-sm" @click="doSearch">Search</button>
      </div>
      <div v-else>
        <button class="btn-primary text-sm" @click="doSearch">Search</button>
      </div>

      <!-- Tag chips (keyword mode only) -->
      <div v-if="mode === 'keyword' && allTags.length" class="flex flex-wrap gap-1.5">
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

    <!-- Model-not-installed notice for smart search -->
    <div v-else-if="modelUnavailable" class="rounded-xl border border-amber-700/40 bg-amber-900/20 p-4 text-sm text-amber-200">
      <p class="font-medium mb-1">Smart search isn’t set up yet</p>
      <p class="text-amber-200/80">
        Install the local AI model (runs entirely on your machine, no cost):
      </p>
      <pre class="mt-2 bg-black/30 rounded-lg p-2 text-xs overflow-x-auto">pip install -r requirements-ai.txt</pre>
      <p class="text-amber-200/80 mt-2">Then run <span class="font-mono">Analyze library</span> from the Cleanup tab to index your photos.</p>
    </div>

    <div v-else-if="needsIndex" class="rounded-xl border border-blue-700/40 bg-blue-900/20 p-4 text-sm text-blue-200">
      <p>No photos indexed for smart search yet. Run <span class="font-mono">Analyze library</span> from the Cleanup tab first.</p>
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

const mode = ref('keyword')
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
const modelUnavailable = ref(false)
const needsIndex = ref(false)

onMounted(async () => {
  const { data } = await tagsApi.list()
  allTags.value = data.tags
})

function setMode(m) {
  mode.value = m
  modelUnavailable.value = false
  needsIndex.value = false
  searched.value = false
  results.value = []
}

function toggleTag(tag) {
  activeTag.value = activeTag.value === tag ? null : tag
  doSearch()
}

async function doSearch() {
  loading.value = true
  searched.value = true
  modelUnavailable.value = false
  needsIndex.value = false
  try {
    if (mode.value === 'smart') {
      if (!query.value) { results.value = []; return }
      try {
        const { data } = await searchApi.semantic(query.value)
        results.value = data.photos
        if (data.hint && data.count === 0) needsIndex.value = true
      } catch (e) {
        if (e.response?.status === 503) modelUnavailable.value = true
        else throw e
      }
    } else {
      const params = {}
      if (query.value) params.q = query.value
      if (activeTag.value) params.tag = activeTag.value
      if (dateFrom.value) params.date_from = dateFrom.value
      if (dateTo.value) params.date_to = dateTo.value
      if (camera.value) params.camera = camera.value
      const { data } = await searchApi.search(params)
      results.value = data.photos
    }
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
