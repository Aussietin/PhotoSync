<template>
  <div class="space-y-4">
    <!-- Header Banner -->
    <div class="flex flex-wrap items-center justify-between gap-3 bg-ink-900/60 p-4 rounded-2xl border border-white/5 backdrop-blur-md">
      <div>
        <h1 class="text-xl font-extrabold tracking-tight text-white flex items-center gap-2">
          <span>Trash & Recycle Bin</span>
          <span class="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-red-500/20 text-red-300 border border-red-400/20">
            {{ photos.length }} {{ photos.length === 1 ? 'item' : 'items' }}
          </span>
        </h1>
        <p class="text-xs text-gray-400 mt-1">
          Deleted items stay here safely until emptied. Originals in your folder are never touched if in-place mode is active.
        </p>
      </div>

      <div v-if="photos.length" class="flex items-center gap-2 flex-wrap">
        <button class="btn-ghost text-xs sm:text-sm py-2 px-3 text-emerald-400 hover:text-emerald-300" @click="restoreAll">
          ↩️ Restore All
        </button>
        <button class="btn-danger text-xs sm:text-sm py-2 px-4 shadow-sm" @click="emptyTrash">
          🗑 Empty Trash
        </button>
      </div>
    </div>

    <!-- Skeletons -->
    <div v-if="loading" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
      <div v-for="i in 12" :key="i" class="card p-2 space-y-2">
        <Skeleton width="100%" height="8rem" rounded="rounded-xl" />
        <Skeleton width="70%" height="0.7rem" />
      </div>
    </div>

    <!-- Photos Grid in Trash -->
    <div v-else-if="photos.length" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
      <div
        v-for="photo in photos"
        :key="photo.id"
        class="card p-2.5 flex flex-col gap-2 bg-ink-900/80 border-white/5 group hover:border-white/20 transition-all shadow-md"
      >
        <div class="aspect-square rounded-xl overflow-hidden bg-ink-850 relative">
          <img
            v-if="photo.thumbnail_url"
            :src="photo.thumbnail_url"
            class="w-full h-full object-cover opacity-75 group-hover:opacity-100 transition-opacity"
          />
          <div v-else class="flex items-center justify-center w-full h-full text-2xl text-gray-600">🖼️</div>

          <span class="absolute top-1.5 right-1.5 text-[10px] font-mono px-1.5 py-0.5 rounded bg-black/60 backdrop-blur-md text-gray-300">
            {{ formatRelative(photo.deleted_at) }}
          </span>
        </div>

        <div class="px-0.5 min-w-0">
          <p class="text-xs truncate font-medium text-gray-300" :title="photo.filename">{{ photo.filename }}</p>
        </div>

        <div class="flex items-center gap-1.5 pt-1 border-t border-white/5">
          <button
            class="flex-1 py-1 px-2 rounded-lg bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 text-[11px] font-semibold transition-colors"
            @click="restore(photo.id)"
          >
            Restore
          </button>
          <button
            class="py-1 px-2 rounded-lg hover:bg-red-500/20 text-red-400 text-[11px] transition-colors"
            title="Permanently remove"
            @click="permanentDelete(photo.id)"
          >
            ✕
          </button>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <EmptyState
      v-else
      icon="🗑️"
      title="Trash is clean and empty"
      subtitle="Items moved to Trash from Triage, Duplicates, or Library will appear here for safe recovery."
    >
      <template #action>
        <router-link to="/" class="btn-ghost text-sm">Return to Library</router-link>
      </template>
    </EmptyState>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { photosApi } from '../api/photos'
import Skeleton from '../components/ui/Skeleton.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import { useToast } from '../composables/useToast'
import { useConfirm } from '../composables/useConfirm'

const { success } = useToast()
const { confirm } = useConfirm()

const photos = ref([])
const loading = ref(false)

onMounted(load)

async function load() {
  loading.value = true
  try {
    const { data } = await photosApi.trash()
    photos.value = data.photos
  } finally {
    loading.value = false
  }
}

async function restore(id) {
  await photosApi.restore(id)
  photos.value = photos.value.filter((p) => p.id !== id)
  success('Photo restored to library')
}

async function permanentDelete(id) {
  const ok = await confirm({
    title: 'Permanently remove photo?',
    message: 'This will erase the photo permanently. This action cannot be undone.',
    confirmText: 'Delete Permanently',
    danger: true,
  })
  if (!ok) return
  await photosApi.permanentDelete(id)
  photos.value = photos.value.filter((p) => p.id !== id)
  success('Photo permanently removed')
}

async function restoreAll() {
  const n = photos.value.length
  await photosApi.bulkRestore(photos.value.map((p) => p.id))
  photos.value = []
  success(`Restored ${n} photo${n > 1 ? 's' : ''} to library`)
}

async function emptyTrash() {
  const n = photos.value.length
  const ok = await confirm({
    title: `Permanently delete all ${n} items in Trash?`,
    message: 'All cached thumbnails and managed copies in Trash will be permanently erased. Originals in in-place folder mode will remain untouched.',
    confirmText: 'Empty Trash',
    danger: true,
  })
  if (!ok) return
  await photosApi.emptyTrash()
  photos.value = []
  success('Trash emptied successfully')
}

function formatRelative(iso) {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}
</script>
