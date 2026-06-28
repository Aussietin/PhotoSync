<template>
  <div class="max-w-lg mx-auto space-y-6">
    <h1 class="text-xl font-bold">Import from Folder</h1>
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
        {{ loading ? 'Scanning…' : 'Start import' }}
      </button>
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

const folderPath = ref('')
const recursive = ref(true)
const loading = ref(false)
const result = ref(null)
const error = ref(null)

async function runImport() {
  loading.value = true
  result.value = null
  error.value = null
  try {
    const { data } = await photosApi.importFolder(folderPath.value.trim(), recursive.value)
    result.value = data
  } catch (e) {
    error.value = e.response?.data?.detail ?? 'Import failed. Check the folder path.'
  } finally {
    loading.value = false
  }
}
</script>
