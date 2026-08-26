<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3 bg-ink-900/60 p-4 rounded-2xl border border-white/5 backdrop-blur-md">
      <div>
        <h1 class="text-xl font-extrabold tracking-tight text-white flex items-center gap-2">
          <span>Albums & Collections</span>
          <span class="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-brand-500/20 text-brand-300 border border-brand-400/20">
            {{ albums.length }}
          </span>
        </h1>
        <p class="text-xs text-gray-400 mt-1">
          Curated collections and folders organized by trips, events, or categories.
        </p>
      </div>

      <button class="btn-primary text-xs sm:text-sm py-2 px-4 shadow-sm" @click="showCreate = true">
        ＋ Create Album
      </button>
    </div>

    <!-- Skeletons -->
    <div v-if="loading" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      <div v-for="i in 8" :key="i" class="card p-3 space-y-2">
        <div class="skeleton aspect-square rounded-2xl" :style="{ animationDelay: `${i * 80}ms` }" />
        <Skeleton width="70%" height="0.9rem" />
        <Skeleton width="40%" height="0.7rem" />
      </div>
    </div>

    <!-- Albums Grid -->
    <div v-else-if="albums.length" class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
      <router-link
        v-for="album in albums"
        :key="album.id"
        :to="`/albums/${album.id}`"
        class="card p-3 flex flex-col gap-2.5 bg-ink-900/85 border-white/5 hover:border-white/20 transition-all duration-200 group hover:-translate-y-1 shadow-md"
      >
        <!-- Cover -->
        <div class="aspect-square bg-ink-850 rounded-2xl overflow-hidden relative border border-white/5">
          <img
            v-if="album.cover_url"
            :src="album.cover_url"
            :alt="album.name"
            class="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
          <div v-else class="flex items-center justify-center w-full h-full text-5xl text-gray-700">
            🗂️
          </div>
          <!-- Photo Count Overlay Pill -->
          <span class="absolute bottom-2 right-2 badge bg-black/60 backdrop-blur-md text-white font-mono text-[10px]">
            {{ album.photo_count }} {{ album.photo_count === 1 ? 'item' : 'items' }}
          </span>
        </div>

        <!-- Info -->
        <div class="px-1">
          <p class="font-bold text-sm text-gray-100 truncate group-hover:text-brand-300 transition-colors">{{ album.name }}</p>
          <p v-if="album.description" class="text-xs text-gray-400 mt-0.5 truncate">{{ album.description }}</p>
        </div>
      </router-link>
    </div>

    <EmptyState
      v-else
      icon="🗂️"
      title="No albums created yet"
      subtitle="Group your photos into trips, holidays, client shoots, or favorite highlights."
    >
      <template #action>
        <button class="btn-primary text-sm" @click="showCreate = true">＋ Create Your First Album</button>
      </template>
    </EmptyState>

    <!-- Create Album Modal -->
    <Teleport to="body">
      <div v-if="showCreate" class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4" @click.self="showCreate = false">
        <div class="glass shadow-2xl p-6 w-full max-w-sm space-y-4 rounded-3xl border border-white/10 animate-scale-in">
          <h2 class="font-extrabold text-lg flex items-center gap-2 text-white"><span>🗂️</span> Create New Album</h2>
          <div class="space-y-3">
            <input
              v-model="newName"
              type="text"
              placeholder="Album Title (e.g. Kyoto Trip 2026)"
              class="input text-sm"
              autofocus
              @keydown.enter="createAlbum"
            />
            <textarea
              v-model="newDesc"
              placeholder="Album notes or description (optional)"
              rows="2"
              class="input text-sm resize-none"
            />
          </div>
          <div class="flex gap-2 pt-1">
            <button class="btn-ghost flex-1 text-xs" @click="showCreate = false">Cancel</button>
            <button class="btn-primary flex-1 text-xs" :disabled="!newName.trim()" @click="createAlbum">Create</button>
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
