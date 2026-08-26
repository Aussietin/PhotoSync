<template>
  <div class="space-y-4">
    <!-- Search Header & Mode Selector -->
    <div class="flex flex-wrap items-center justify-between gap-3 bg-ink-900/60 p-4 rounded-2xl border border-white/5 backdrop-blur-md">
      <div>
        <h1 class="text-xl font-extrabold tracking-tight text-white flex items-center gap-2">
          <span>Search Library</span>
          <span v-if="searched" class="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-brand-500/20 text-brand-300 border border-brand-400/20">
            {{ results.length }} {{ results.length === 1 ? 'match' : 'matches' }}
          </span>
        </h1>
        <p class="text-xs text-gray-400 mt-1">
          {{ mode === 'smart' ? 'Local natural language AI search running offline on your PC.' : 'Filter precisely by filenames, tags, camera equipment, or date ranges.' }}
        </p>
      </div>

      <!-- Mode Toggle -->
      <div class="flex gap-1 bg-ink-850 p-1 rounded-xl border border-white/5">
        <button
          class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all select-none"
          :class="mode === 'keyword' ? 'bg-brand-500 text-white shadow-sm' : 'text-gray-400 hover:text-white'"
          @click="setMode('keyword')"
        >
          🔍 Exact Filters
        </button>
        <button
          class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all select-none flex items-center gap-1"
          :class="mode === 'smart' ? 'bg-brand-gradient text-white shadow-glow' : 'text-gray-400 hover:text-white'"
          @click="setMode('smart')"
        >
          <span>✨</span>
          <span>Smart AI</span>
        </button>
      </div>
    </div>

    <!-- Search Input Form -->
    <div class="card p-4 space-y-3 bg-ink-900/80 border-white/5">
      <div class="flex items-center gap-2">
        <SearchBar
          v-model="query"
          :placeholder="mode === 'smart' ? 'Describe what you are looking for, e.g. “dog playing at beach”, “white receipt”…' : 'Search by filename, note caption, or keyword…'"
          class="flex-1"
          @search="doSearch"
        />
        <button class="btn-primary text-xs py-2.5 px-4 flex-shrink-0" :disabled="loading" @click="doSearch">
          <Spinner v-if="loading" :size="16" />
          {{ loading ? 'Searching…' : 'Search' }}
        </button>
      </div>

      <!-- Smart search prompt hints -->
      <div v-if="mode === 'smart'" class="flex items-center gap-1.5 flex-wrap pt-1">
        <span class="text-xs text-gray-500 font-medium mr-1">Suggestions:</span>
        <button
          v-for="hint in ['Dog at beach', 'Receipts & bills', 'Sunsets & landscapes', 'Food & drinks', 'Screenshots & text']"
          :key="hint"
          class="chip-muted text-[11px] py-1 px-2.5"
          @click="applyHint(hint)"
        >
          {{ hint }}
        </button>
      </div>

      <!-- Keyword filter grid -->
      <div v-if="mode === 'keyword'" class="grid grid-cols-1 sm:grid-cols-3 gap-2.5 pt-1">
        <div>
          <label class="block text-[11px] text-gray-400 mb-1">From Date</label>
          <input v-model="dateFrom" type="date" class="input text-xs py-2" />
        </div>
        <div>
          <label class="block text-[11px] text-gray-400 mb-1">To Date</label>
          <input v-model="dateTo" type="date" class="input text-xs py-2" />
        </div>
        <div>
          <label class="block text-[11px] text-gray-400 mb-1">Camera / Device</label>
          <input v-model="camera" class="input text-xs py-2" placeholder="e.g. iPhone 15 Pro" />
        </div>
      </div>

      <!-- Tag chips (keyword mode only) -->
      <div v-if="mode === 'keyword' && allTags.length" class="flex flex-wrap gap-1.5 pt-1">
        <span class="text-xs text-gray-500 mr-1 self-center">Tags:</span>
        <button
          v-for="tag in allTags"
          :key="tag"
          class="text-xs"
          :class="activeTag === tag ? 'chip-active' : 'chip-muted'"
          @click="toggleTag(tag)"
        >{{ tag }}</button>
      </div>
    </div>

    <!-- Results Section -->
    <PhotoGridSkeleton v-if="loading && !results.length" :count="12" />

    <!-- Model not installed notice -->
    <div v-else-if="modelUnavailable" class="card p-5 border-amber-500/30 bg-amber-950/20 text-amber-200 text-sm space-y-2">
      <div class="font-bold flex items-center gap-2 text-amber-300">
        <span>⚠️</span> Smart Search Model Not Yet Installed
      </div>
      <p class="text-xs text-amber-200/80">
        To use offline AI semantic search on this machine without cloud API fees, install the requirements:
      </p>
      <pre class="bg-black/40 border border-white/10 rounded-xl p-3 font-mono text-xs text-brand-300 select-all overflow-x-auto">pip install -r requirements-ai.txt</pre>
      <p class="text-xs text-amber-200/80">
        Then visit the <router-link to="/cleanup" class="underline font-semibold text-brand-300">Cleanup</router-link> tab to run <strong>Analyze Library</strong> to compute embeddings.
      </p>
    </div>

    <div v-else-if="needsIndex" class="card p-5 border-brand-500/30 bg-brand-950/20 text-brand-200 text-sm">
      <p>No photos have semantic search embeddings yet. Run <router-link to="/cleanup" class="underline font-semibold">Analyze library</router-link> from the Cleanup tab first.</p>
    </div>

    <template v-else-if="searched && results.length">
      <!-- Batch bar -->
      <div class="flex items-center justify-between gap-2">
        <div class="flex items-center gap-2">
          <button
            class="btn-ghost text-xs py-1.5 px-3"
            :class="sel.selecting.value && 'bg-brand-500/20 border-brand-400/40 text-brand-200'"
            @click="sel.selecting.value ? sel.clear() : (sel.selecting.value = true)"
          >
            {{ sel.selecting.value ? 'Cancel' : 'Select' }}
          </button>
          <button
            v-if="sel.selecting.value"
            class="btn-ghost text-xs py-1.5 px-3"
            @click="sel.selectAll(results.map(p => p.id))"
          >
            Select All ({{ results.length }})
          </button>
        </div>
      </div>

      <PhotoGrid
        :photos="results"
        :selection="sel"
        :selection-mode="sel.selecting.value"
        :show-upload-hint="false"
        @select="openModal"
        @toggle-favorite="toggleFavorite"
      />
    </template>

    <EmptyState
      v-else-if="searched"
      icon="🔍"
      title="No matching photos found"
      subtitle="Try a broader description, different tag, or clear date filters."
    />

    <EmptyState
      v-else
      icon="🔎"
      title="Explore your library"
      subtitle="Type a natural description in Smart AI mode or use exact filters to locate specific shots."
    />

    <PhotoModal
      v-if="selected"
      :photo="selected"
      @close="selected = null"
      @delete="deletePhoto"
      @toggle-favorite="toggleFavorite"
    />

    <BatchToolbar
      :count="sel.count.value"
      @favorite="bulkFavorite"
      @delete="bulkDelete"
      @download="bulkDownload"
      @clear="sel.clear()"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { searchApi, tagsApi, photosApi } from '../api/photos'
import { useSelection } from '../composables/useSelection'
import SearchBar from '../components/SearchBar.vue'
import PhotoGrid from '../components/PhotoGrid.vue'
import PhotoGridSkeleton from '../components/ui/PhotoGridSkeleton.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import Spinner from '../components/ui/Spinner.vue'
import PhotoModal from '../components/PhotoModal.vue'
import BatchToolbar from '../components/BatchToolbar.vue'
import { useToast } from '../composables/useToast'
import { useConfirm } from '../composables/useConfirm'

const { success, error: toastError } = useToast()
const { confirm } = useConfirm()

const mode = ref('smart')
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
const sel = useSelection()

onMounted(async () => {
  try {
    const { data } = await tagsApi.list()
    allTags.value = data.tags
  } catch { /* non-fatal */ }
})

function setMode(m) {
  mode.value = m
  modelUnavailable.value = false
  needsIndex.value = false
  searched.value = false
  results.value = []
  sel.clear()
}

function applyHint(hint) {
  query.value = hint
  doSearch()
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
  sel.clear()
  try {
    if (mode.value === 'smart') {
      if (!query.value.trim()) { results.value = []; return }
      try {
        const { data } = await searchApi.semantic(query.value.trim())
        results.value = data.photos
        if (data.hint && data.count === 0) needsIndex.value = true
      } catch (e) {
        if (e.response?.status === 503) modelUnavailable.value = true
        else throw e
      }
    } else {
      const params = {}
      if (query.value.trim()) params.q = query.value.trim()
      if (activeTag.value) params.tag = activeTag.value
      if (dateFrom.value) params.date_from = dateFrom.value
      if (dateTo.value) params.date_to = dateTo.value
      if (camera.value.trim()) params.camera = camera.value.trim()
      const { data } = await searchApi.search(params)
      results.value = data.photos
    }
  } finally {
    loading.value = false
  }
}

function openModal(photo) {
  if (sel.selecting.value) { sel.toggle(photo.id); return }
  selected.value = photo
}

async function deletePhoto(id) {
  await photosApi.delete(id)
  results.value = results.value.filter((p) => p.id !== id)
  selected.value = null
  success('Moved photo to Trash')
}

async function toggleFavorite(id) {
  const { data } = await photosApi.toggleFavorite(id)
  const photo = results.value.find((p) => p.id === id)
  if (photo) photo.is_favorite = data.is_favorite
  if (selected.value?.id === id) selected.value = { ...selected.value, is_favorite: data.is_favorite }
}

async function bulkDelete() {
  const n = sel.count.value
  await photosApi.bulkDelete(sel.ids.value)
  results.value = results.value.filter((p) => !sel.selected.value.has(p.id))
  sel.clear()
  success(`Moved ${n} to Trash`)
}

async function bulkFavorite() {
  const n = sel.count.value
  await photosApi.bulkFavorite(sel.ids.value)
  results.value.forEach((p) => { if (sel.selected.value.has(p.id)) p.is_favorite = true })
  sel.clear()
  success(`Added ${n} to Favorites`)
}

async function bulkDownload() {
  try {
    const { data } = await photosApi.downloadZip(sel.ids.value)
    const url = URL.createObjectURL(data)
    const a = document.createElement('a')
    a.href = url
    a.download = 'search-results.zip'
    a.click()
    URL.revokeObjectURL(url)
    success('Downloading ZIP export')
  } catch {
    toastError('Could not download ZIP')
  }
}
</script>
