<template>
  <div>
    <div class="flex items-center justify-between mb-5">
      <h1 class="text-2xl font-bold tracking-tight">Duplicates <span class="text-gray-500 font-normal text-base">({{ duplicates.length }})</span></h1>
      <button
        v-if="duplicates.length"
        class="btn-danger text-sm"
        @click="deleteAll"
      >
        🗑 Delete all duplicates
      </button>
    </div>

    <div v-if="loading" class="space-y-1">
      <div v-for="i in 6" :key="i" class="card flex items-center gap-3 p-3">
        <Skeleton width="4rem" height="4rem" rounded="rounded-xl" />
        <div class="flex-1 space-y-2">
          <Skeleton width="55%" height="0.8rem" />
          <Skeleton width="30%" height="0.65rem" />
        </div>
      </div>
    </div>

    <div v-else-if="duplicates.length" class="space-y-1">
      <div
        v-for="photo in duplicates"
        :key="photo.id"
        class="card flex items-center gap-3 p-3"
      >
        <img
          v-if="photo.thumbnail_url"
          :src="photo.thumbnail_url"
          class="w-16 h-16 object-cover rounded-xl flex-shrink-0"
        />
        <div class="flex-1 min-w-0">
          <p class="text-sm truncate text-gray-300">{{ photo.filename }}</p>
          <p class="text-xs text-gray-500 mt-0.5">Duplicate of photo #{{ photo.duplicate_of_id }}</p>
        </div>
        <button
          class="btn-ghost text-red-400 hover:text-red-300 text-sm flex-shrink-0"
          @click="deleteOne(photo.id)"
        >Delete</button>
      </div>
    </div>

    <EmptyState
      v-else
      icon="✅"
      title="No duplicates found"
      subtitle="Your library is clean!"
    />
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

const duplicates = ref([])
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await photosApi.duplicates()
    duplicates.value = data.duplicates
  } finally {
    loading.value = false
  }
})

async function deleteOne(id) {
  await photosApi.delete(id)
  duplicates.value = duplicates.value.filter((p) => p.id !== id)
}

async function deleteAll() {
  const n = duplicates.value.length
  const ok = await confirm({
    title: `Delete all ${n} duplicates?`,
    message: 'Deleted photos go to Trash, where you can restore them.',
    confirmText: 'Delete all',
    danger: true,
  })
  if (!ok) return
  await Promise.all(duplicates.value.map((p) => photosApi.delete(p.id)))
  duplicates.value = []
  success(`Moved ${n} duplicates to Trash`)
}
</script>
