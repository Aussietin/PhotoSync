<template>
  <div class="max-w-lg mx-auto space-y-6">
    <h1 class="text-2xl font-bold tracking-tight">Import from Folder</h1>
    <p class="text-sm text-gray-400">
      Point PhotoSync at a folder on the server's filesystem to bulk-import images without re-uploading.
      Useful for migrating an existing photo library.
    </p>

    <div class="card p-5 space-y-4">
      <div>
        <label class="block text-xs text-gray-500 mb-1.5">Server folder path</label>
        <input
          v-model="folderPath"
          type="text"
          placeholder="/home/user/Pictures"
          class="input font-mono"
        />
      </div>

      <label class="flex items-center gap-2 text-sm text-gray-300 cursor-pointer select-none">
        <input v-model="recursive" type="checkbox" class="accent-brand-500" />
        Scan subfolders recursively
      </label>

      <button
        class="btn-primary w-full"
        :disabled="!folderPath.trim() || loading"
        @click="runImport"
      >
        <Spinner v-if="loading" :size="16" />
        {{ loading ? 'Importing…' : '📥 Start import' }}
      </button>

      <!-- Live progress -->
      <div v-if="job && job.status !== 'done'" class="space-y-1.5">
        <div class="flex justify-between text-xs text-gray-500">
          <span>{{ job.status === 'error' ? 'Failed' : 'Importing & analyzing…' }}</span>
          <span v-if="job.percent != null">{{ job.processed }} / {{ job.total }} ({{ job.percent }}%)</span>
        </div>
        <ProgressBar :value="job.percent ?? 5" :active="job.status !== 'error'" />
      </div>
    </div>

    <!-- Result -->
    <div v-if="result" class="card p-5 space-y-2">
      <h2 class="font-semibold text-green-400">Import complete</h2>
      <div class="grid grid-cols-3 gap-3 text-center text-sm">
        <div class="bg-gray-800 rounded-xl p-3">
          <div class="text-2xl font-bold text-gray-100">{{ result.imported }}</div>
          <div class="text-xs text-gray-500 mt-0.5">Imported</div>
        </div>
        <div class="bg-gray-800 rounded-xl p-3">
          <div class="text-2xl font-bold text-gray-100">{{ result.skipped }}</div>
          <div class="text-xs text-gray-500 mt-0.5">Skipped</div>
        </div>
        <div class="bg-gray-800 rounded-xl p-3">
          <div class="text-2xl font-bold text-yellow-400">{{ result.duplicates_found }}</div>
          <div class="text-xs text-gray-500 mt-0.5">Duplicates</div>
        </div>
      </div>
      <router-link to="/" class="btn-ghost w-full text-center text-sm block mt-2">View library →</router-link>
    </div>

    <div v-if="error" class="card p-4 border border-red-900">
      <p class="text-sm text-red-400">{{ error }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { photosApi } from '../api/photos'
import { useJob } from '../composables/useJob'
import Spinner from '../components/ui/Spinner.vue'
import ProgressBar from '../components/ui/ProgressBar.vue'

const folderPath = ref('')
const recursive = ref(true)
const loading = ref(false)
const result = ref(null)
const error = ref(null)
const { job, track } = useJob()

async function runImport() {
  loading.value = true
  result.value = null
  error.value = null
  try {
    const { data } = await photosApi.importFolder(folderPath.value.trim(), recursive.value)
    // Backend now returns a job id and processes in the background.
    await track(data.job_id, {
      onDone: (j) => { result.value = j.result; loading.value = false },
      onError: (j) => { error.value = j.message || 'Import failed.'; loading.value = false },
    })
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Import failed. Check the folder path.'
    loading.value = false
  }
}
</script>
