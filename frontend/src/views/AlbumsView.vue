<template>
  <div>
    <div class="flex items-center justify-between mb-5">
      <h1 class="text-2xl font-bold tracking-tight">Albums</h1>
      <button class="btn-primary text-sm" @click="showCreate = true">＋ New Album</button>
    </div>

    <div v-if="loading" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      <div v-for="i in 8" :key="i" class="card">
        <div class="skeleton aspect-square !rounded-none" :style="{ animationDelay: `${i * 80}ms` }" />
        <div class="p-3 space-y-2">
          <Skeleton width="70%" height="0.9rem" />
          <Skeleton width="40%" height="0.7rem" />
        </div>
      </div>
    </div>

    <div v-else-if="albums.length" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      <router-link
        v-for="album in albums"
        :key="album.id"
        :to="`/albums/${album.id}`"
        class="card surface-hover group cursor-pointer hover:-translate-y-0.5 transition-transform"
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

    <EmptyState
      v-else
      icon="🗂️"
      title="No albums yet"
      subtitle="Create an album to group photos by trip, event, or anything you like."
    >
      <template #action>
        <button class="btn-primary text-sm" @click="showCreate = true">＋ New Album</button>
      </template>
    </EmptyState>

    <!-- Create album modal -->
    <Teleport to="body">
      <div v-if="showCreate" class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4" @click.self="showCreate = false">
        <div class="glass shadow-soft p-6 w-full max-w-sm space-y-4 animate-scale-in">
          <h2 class="font-semibold text-lg flex items-center gap-2"><span>🗂️</span> New Album</h2>
          <input
            v-model="newName"
            type="text"
            placeholder="Album name"
            class="input"
            @keydown.enter="createAlbum"
          />
          <textarea
            v-model="newDesc"
            placeholder="Description (optional)"
            rows="2"
            class="input resize-none"
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
import Skeleton from '../components/ui/Skeleton.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import { useToast } from '../composables/useToast'

const { success } = useToast()

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
  success(`Created “${data.name}”`)
  newName.value = ''
  newDesc.value = ''
  showCreate.value = false
}
</script>
