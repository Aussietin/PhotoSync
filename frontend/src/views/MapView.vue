<template>
  <div class="space-y-3">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold tracking-tight">Map</h1>
      <span class="text-sm text-gray-500">{{ pins.length }} photo{{ pins.length !== 1 ? 's' : '' }} with GPS</span>
    </div>

    <div v-if="loading" class="skeleton rounded-2xl" style="height: 70vh">
      <div class="h-full grid place-items-center">
        <Spinner :size="32" label="Loading map…" />
      </div>
    </div>

    <EmptyState
      v-else-if="!pins.length"
      icon="📍"
      title="No photos with GPS data yet"
      subtitle="GPS is embedded by iPhone when Location Services are enabled for the Camera."
    />

    <div v-else ref="mapEl" class="rounded-2xl overflow-hidden border border-white/10 shadow-soft" style="height: 70vh" />

    <!-- Detail popup (shown when pin clicked) -->
    <Teleport to="body">
      <div
        v-if="selected"
        class="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 p-4"
        @click.self="selected = null"
      >
        <div class="card p-4 w-full max-w-xs space-y-3">
          <img
            v-if="selected.thumbnail_url"
            :src="selected.thumbnail_url"
            class="w-full aspect-square object-cover rounded-xl"
          />
          <div class="text-xs text-gray-400 space-y-1">
            <p v-if="selected.taken_at">📅 {{ formatDate(selected.taken_at) }}</p>
            <p>📍 {{ selected.lat.toFixed(5) }}, {{ selected.lon.toFixed(5) }}</p>
          </div>
          <router-link :to="`/?highlight=${selected.id}`" class="btn-primary w-full text-sm text-center block">View in library</router-link>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { photosApi } from '../api/photos'
import Spinner from '../components/ui/Spinner.vue'
import EmptyState from '../components/ui/EmptyState.vue'

const mapEl = ref(null)
const pins = ref([])
const loading = ref(false)
const selected = ref(null)
let mapInstance = null

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await photosApi.map()
    pins.value = data
  } finally {
    loading.value = false
  }

  if (!pins.value.length) return

  // Dynamic import keeps Leaflet out of the initial bundle
  const L = (await import('leaflet')).default
  await import('leaflet/dist/leaflet.css')

  // Fix default marker icon path broken by bundlers
  delete L.Icon.Default.prototype._getIconUrl
  L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
  })

  mapInstance = L.map(mapEl.value).setView([0, 0], 2)

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    maxZoom: 19,
  }).addTo(mapInstance)

  const bounds = []
  for (const pin of pins.value) {
    const thumb = pin.thumbnail_url
      ? `<img src="${pin.thumbnail_url}" style="width:80px;height:80px;object-fit:cover;border-radius:8px;cursor:pointer" />`
      : ''
    const marker = L.marker([pin.lat, pin.lon])
      .addTo(mapInstance)
      .bindPopup(thumb)
      .on('click', () => { selected.value = pin })
    bounds.push([pin.lat, pin.lon])
  }

  if (bounds.length) mapInstance.fitBounds(bounds, { padding: [40, 40] })
})

onBeforeUnmount(() => {
  if (mapInstance) { mapInstance.remove(); mapInstance = null }
})

function formatDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}
</script>
