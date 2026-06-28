<template>
  <div>
    <div class="flex items-center justify-between mb-5">
      <h1 class="text-xl font-bold">Library <span class="text-gray-500 font-normal text-base">({{ total }} photos)</span></h1>
      <label class="flex items-center gap-2 text-xs text-gray-400 cursor-pointer select-none">
        <input v-model="showDuplicates" type="checkbox" class="accent-brand-500" />
        Show duplicates
      </label>
    </div>

    <div v-if="loading" class="flex justify-center py-20">
      <span class="text-gray-500 animate-pulse">Loading…</span>
    </div>

    <PhotoGrid v-else :photos="photos" @select="selected = $event" />

    <!-- Infinite-scroll sentinel -->
    <div ref="sentinel" class="h-10" />

    <PhotoModal v-if="selected" :photo="selected" @close="selected = null" @delete="deletePhoto" />
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { photosApi } from '../api/photos'
import PhotoGrid from '../components/PhotoGrid.vue'
import PhotoModal from '../components/PhotoModal.vue'

const photos = ref([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const showDuplicates = ref(false)
const selected = ref(null)
const sentinel = ref(null)

async function load(reset = false) {
  if (loading.value) return
  loading.value = true
  try {
    const { data } = await photosApi.list({ page: page.value, per_page: 50, include_duplicates: showDuplicates.value })
    if (reset) photos.value = data.photos
    else photos.value.push(...data.photos)
    total.value = data.total
  } finally {
    loading.value = false
  }
}

watch(showDuplicates, () => { page.value = 1; load(true) })

async function deletePhoto(id) {
  await photosApi.delete(id)
  photos.value = photos.value.filter((p) => p.id !== id)
  selected.value = null
  total.value--
}

let observer
onMounted(() => {
  load(true)
  observer = new IntersectionObserver(([entry]) => {
    if (entry.isIntersecting && photos.value.length < total.value) {
      page.value++
      load()
    }
  })
  if (sentinel.value) observer.observe(sentinel.value)
})
onBeforeUnmount(() => observer?.disconnect())
</script>
