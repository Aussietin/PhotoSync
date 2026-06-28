<template>
  <div class="max-w-lg mx-auto space-y-6">
    <h1 class="text-xl font-bold">Import from Folder</h1>
    <p class="text-sm text-gray-400">
      Point PhotoSync at a folder on the server's filesystem to bulk-import images without re-uploading.
      Useful for migrating an existing photo library.
    </p>

    <!-- Getting photos off the phone -->
    <div class="card p-5 space-y-3">
      <h2 class="font-semibold text-sm">How to get photos from your iPhone to this machine</h2>
      <div class="space-y-3 text-sm text-gray-400">
        <div>
          <p class="font-medium text-gray-300">Option A — Finder / Image Capture (USB, fastest)</p>
          <ol class="mt-1.5 ml-4 space-y-1 list-decimal marker:text-gray-600">
            <li>Plug iPhone into Mac with a Lightning or USB-C cable.</li>
            <li>Open <span class="font-medium text-gray-300">Image Capture</span> (in Applications) or click the phone in Finder's sidebar.</li>
            <li>Select all photos (<kbd class="text-xs bg-gray-800 px-1.5 py-0.5 rounded">⌘A</kbd>) and click <span class="font-medium text-gray-300">Import All</span> → choose a destination folder.</li>
            <li>Enter that folder path below and click <span class="font-medium text-gray-300">Start import</span>.</li>
          </ol>
        </div>
        <div>
          <p class="font-medium text-gray-300">Option B — iCloud Photos (wireless)</p>
          <ol class="mt-1.5 ml-4 space-y-1 list-decimal marker:text-gray-600">
            <li>On the Mac, open <span class="font-medium text-gray-300">Photos</span> app → Preferences → iCloud → enable "Download Originals to this Mac".</li>
            <li>Wait for the full-resolution download to finish (can take hours for large libraries).</li>
            <li>The originals land in <span class="font-mono text-xs bg-gray-800 px-1.5 py-0.5 rounded">~/Pictures/Photos Library.photoslibrary/originals</span> — use that path below, with <span class="font-medium text-gray-300">Scan subfolders</span> checked.</li>
          </ol>
        </div>
        <div>
          <p class="font-medium text-gray-300">Option C — AirDrop to Mac</p>
          <ol class="mt-1.5 ml-4 space-y-1 list-decimal marker:text-gray-600">
            <li>On iPhone: Photos → select all → tap Share → AirDrop → your Mac.</li>
            <li>Files land in <span class="font-mono text-xs bg-gray-800 px-1.5 py-0.5 rounded">~/Downloads</span> — use that as the folder path below.</li>
            <li>Best for batches of hundreds; tedious for 20k+.</li>
          </ol>
        </div>
      </div>
    </div>

    <div class="card p-5 space-y-4">
      <div>
        <label class="block text-xs text-gray-500 mb-1.5">Server folder path</label>
        <input
          v-model="folderPath"
          type="text"
          placeholder="/home/user/Pictures"
          class="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-sm font-mono focus:outline-none focus:border-brand-500"
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
        {{ loading ? 'Importing…' : 'Start import' }}
      </button>

      <!-- Live progress -->
      <div v-if="job && job.status !== 'done'" class="space-y-1">
        <div class="flex justify-between text-xs text-gray-500">
          <span>{{ job.status === 'error' ? 'Failed' : 'Importing & analyzing…' }}</span>
          <span v-if="job.percent != null">{{ job.processed }} / {{ job.total }} ({{ job.percent }}%)</span>
        </div>
        <div class="w-full bg-gray-800 rounded-full h-2 overflow-hidden">
          <div class="h-full bg-brand-500 transition-all duration-300" :style="{ width: `${job.percent ?? 5}%` }" />
        </div>
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
