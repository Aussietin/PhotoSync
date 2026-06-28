<template>
  <div>
    <div class="flex items-center justify-between mb-5">
      <h1 class="text-xl font-bold">Albums</h1>
      <button class="btn-primary text-sm" @click="showCreate = true">+ New Album</button>
    </div>

    <div v-if="loading" class="flex justify-center py-20">
      <span class="text-gray-500 animate-pulse">Loading…</span>
    </div>

    <div v-else-if="albums.length" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      <router-link
        v-for="album in albums"
        :key="album.id"
        :to="`/albums/${album.id}`"
        class="card group cursor-pointer"
      >
        <!-- Cover -->
        <div class="aspect-square bg-gray-800 overflow-hidden">
          <img
            v-if="album.cover_url"
            :src="album.cover_url"
            :alt="album.name"
            class="w-full h-full object-cover transition-transform duration-200 group-hover:scale-105"
          />
          <div v-else class="flex items-center justify-center w-full h-full text-5xl text-gray-700">
            🗂️
          </div>
        </div>
        <!-- Info -->
        <div class="p-3">
          <p class="font-medium text-sm text-gray-200 truncate">{{ album.name }}</p>
          <p class="text-xs text-gray-500 mt-0.5">{{ album.photo_count }} photo{{ album.photo_count !== 1 ? 's' : '' }}</p>
        </div>
      </router-link>
    </div>

    <div v-else class="flex flex-col items-center py-20 text-gray-600">
      <span class="text-5xl mb-4">🗂️</span>
      <p>No albums yet — create one to organise your photos.</p>
    </div>

    <!-- Create album modal -->
    <Teleport to="body">
      <div v-if="showCreate" class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" @click.self="showCreate = false">
        <div class="card p-6 w-full max-w-sm space-y-4">
          <h2 class="font-semibold text-lg">New Album</h2>
          <input
            v-model="newName"
            type="text"
            placeholder="Album name"
            class="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:border-brand-500"
            @keydown.enter="createAlbum"
          />
          <textarea
            v-model="newDesc"
            placeholder="Description (optional)"
            rows="2"
            class="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2 text-sm resize-none focus:outline-none focus:border-brand-500"
          />
          <div class="flex gap-2">
            <button class="btn-ghost flex-1" @click="showCreate = false">Cancel</button>
            <button class="btn-primary flex-1" :disabled="!newName.trim()" @click="createAlbum">Create</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { albumsApi } from '../api/photos'

const albums = ref([])
const loading = ref(false)
const showCreate = ref(false)
const newName = ref('')
const newDesc = ref('')

onMounted(load)

async function load() {
  loading.value = true
  try {
    const { data } = await albumsApi.list()
    albums.value = data.albums
  } finally {
    loading.value = false
  }
}

async function createAlbum() {
  if (!newName.value.trim()) return
  const { data } = await albumsApi.create(newName.value.trim(), newDesc.value.trim() || null)
  albums.value.unshift(data)
  newName.value = ''
  newDesc.value = ''
  showCreate.value = false
}
</script>
