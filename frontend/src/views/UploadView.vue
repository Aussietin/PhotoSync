<template>
  <div class="max-w-xl mx-auto">
    <h1 class="text-2xl font-bold tracking-tight mb-6">Upload Photos</h1>

    <UploadZone @files="onFiles" />

    <!-- Queue -->
    <div v-if="queue.length" class="mt-6 space-y-2">
      <div
        v-for="item in queue"
        :key="item.name"
        class="card p-3 flex items-center gap-3"
      >
        <img
          v-if="item.preview"
          :src="item.preview"
          class="w-12 h-12 object-cover rounded-lg flex-shrink-0"
        />
        <div class="flex-1 min-w-0">
          <p class="text-sm truncate text-gray-300">{{ item.name }}</p>
          <div class="mt-1.5 h-1.5 bg-ink-800 rounded-full overflow-hidden">
            <div
              class="h-full rounded-full transition-all duration-300"
              :class="item.status === 'error' ? 'bg-red-500' : item.status === 'done' ? 'bg-green-500' : 'bg-brand-gradient'"
              :style="{ width: (item.status === 'done' ? 100 : item.progress) + '%' }"
            />
          </div>
        </div>
        <span class="text-sm flex-shrink-0 w-9 text-right" :class="item.status === 'done' ? 'text-green-400' : item.status === 'error' ? 'text-red-400' : 'text-gray-500'">
          {{ item.status === 'done' ? '✓' : item.status === 'error' ? '✗' : item.progress + '%' }}
        </span>
      </div>

      <button v-if="!uploading" class="btn-primary w-full mt-2" @click="startUpload">
        Upload {{ queue.length }} photo{{ queue.length !== 1 ? 's' : '' }}
      </button>
    </div>

    <p v-if="doneCount" class="mt-4 text-center text-sm text-green-400">
      {{ doneCount }} photo{{ doneCount !== 1 ? 's' : '' }} uploaded successfully
    </p>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { photosApi } from '../api/photos'
import UploadZone from '../components/UploadZone.vue'
import { useToast } from '../composables/useToast'

const { success, error: toastError } = useToast()

const queue = ref([])
const uploading = ref(false)
const doneCount = ref(0)

function onFiles(files) {
  const newItems = files.map((f) => ({
    file: f,
    name: f.name,
    preview: URL.createObjectURL(f),
    progress: 0,
    status: 'pending',
  }))
  queue.value.push(...newItems)
}

async function startUpload() {
  uploading.value = true
  let ok = 0
  let failed = 0
  for (const item of queue.value.filter((i) => i.status === 'pending')) {
    item.status = 'uploading'
    try {
      await photosApi.upload([item.file], (e) => {
        item.progress = Math.round((e.loaded / e.total) * 100)
      })
      item.status = 'done'
      item.progress = 100
      doneCount.value++
      ok++
    } catch {
      item.status = 'error'
      failed++
    }
  }
  uploading.value = false
  if (ok) success(`Uploaded ${ok} photo${ok > 1 ? 's' : ''}`)
  if (failed) toastError(`${failed} upload${failed > 1 ? 's' : ''} failed`)
}
</script>
