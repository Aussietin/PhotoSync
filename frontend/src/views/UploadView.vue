<template>
  <div class="max-w-2xl mx-auto space-y-6">
    <div class="bg-ink-900/60 p-5 rounded-2xl border border-white/5 backdrop-blur-md">
      <h1 class="text-xl font-extrabold tracking-tight text-white flex items-center gap-2">
        <span>Upload Photos</span>
      </h1>
      <p class="text-xs text-gray-400 mt-1">
        Direct web upload into your local library. Uploaded files are copied into full-resolution local storage.
      </p>
    </div>

    <UploadZone @files="onFiles" />

    <!-- Queue -->
    <div v-if="queue.length" class="space-y-3">
      <div class="flex items-center justify-between text-xs text-gray-400 font-medium px-1">
        <span>Upload Queue ({{ queue.length }} items)</span>
        <button
          v-if="!uploading"
          class="text-gray-500 hover:text-white transition-colors"
          @click="queue = []"
        >Clear</button>
      </div>

      <div
        v-for="item in queue"
        :key="item.name"
        class="card p-3 flex items-center gap-3 bg-ink-900/80 border-white/5 shadow-md"
      >
        <img
          v-if="item.preview"
          :src="item.preview"
          class="w-12 h-12 object-cover rounded-xl flex-shrink-0 bg-ink-850"
        />
        <div class="flex-1 min-w-0">
          <p class="text-xs truncate font-medium text-gray-200">{{ item.name }}</p>
          <div class="mt-2 h-1.5 bg-ink-850 rounded-full overflow-hidden border border-white/5">
            <div
              class="h-full rounded-full transition-all duration-300"
              :class="item.status === 'error' ? 'bg-rose-500' : item.status === 'done' ? 'bg-emerald-500' : 'bg-brand-gradient'"
              :style="{ width: (item.status === 'done' ? 100 : item.progress) + '%' }"
            />
          </div>
        </div>
        <span
          class="text-xs font-mono font-bold flex-shrink-0 w-10 text-right"
          :class="item.status === 'done' ? 'text-emerald-400' : item.status === 'error' ? 'text-rose-400' : 'text-gray-400'"
        >
          {{ item.status === 'done' ? '✓' : item.status === 'error' ? '✕' : item.progress + '%' }}
        </span>
      </div>

      <button
        v-if="!uploading"
        class="btn-primary w-full py-2.5 text-xs font-semibold shadow-glow"
        @click="startUpload"
      >
        Upload {{ queue.length }} photo{{ queue.length !== 1 ? 's' : '' }}
      </button>
    </div>

    <div v-if="doneCount" class="card p-5 bg-emerald-950/20 border-emerald-500/30 text-center space-y-3 shadow-md">
      <p class="text-xs sm:text-sm text-emerald-300 font-medium">
        🎉 {{ doneCount }} photo{{ doneCount !== 1 ? 's' : '' }} uploaded successfully to your local library!
      </p>
      <router-link to="/cleanup" class="btn-primary text-xs py-2 px-5 inline-flex shadow-glow">
        Next: Run Smart Cleanup →
      </router-link>
    </div>
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
