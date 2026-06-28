<template>
  <div class="max-w-xl mx-auto">
    <h1 class="text-xl font-bold mb-6">Upload Photos</h1>

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
          <div class="mt-1 h-1.5 bg-gray-800 rounded-full overflow-hidden">
            <div
              class="h-full bg-brand-500 transition-all duration-300"
              :style="{ width: item.progress + '%' }"
            />
          </div>
        </div>
        <span class="text-xs text-gray-500 flex-shrink-0">
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
  for (const item of queue.value.filter((i) => i.status === 'pending')) {
    item.status = 'uploading'
    try {
      await photosApi.upload([item.file], (e) => {
        item.progress = Math.round((e.loaded / e.total) * 100)
      })
      item.status = 'done'
      item.progress = 100
      doneCount.value++
    } catch {
      item.status = 'error'
    }
  }
  uploading.value = false
}
</script>
