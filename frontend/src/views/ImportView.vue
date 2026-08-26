<template>
  <div class="max-w-2xl mx-auto space-y-6">
    <div class="bg-ink-900/60 p-5 rounded-2xl border border-white/5 backdrop-blur-md">
      <h1 class="text-xl font-extrabold tracking-tight text-white flex items-center gap-2">
        <span>Import from Folder</span>
      </h1>
      <p class="text-xs text-gray-400 mt-1">
        Point PhotoSync at a directory on this machine to register files in-place or copy them into your library.
      </p>
    </div>

    <!-- Mobile Quick-Tip -->
    <div class="card p-4 border-brand-500/30 bg-brand-500/10 text-xs text-gray-300 flex items-start gap-3">
      <span class="text-xl">💡</span>
      <div>
        <strong class="text-white block mb-0.5">Transferring straight from your phone?</strong>
        Open this web app on your phone's browser and use <router-link to="/upload" class="text-brand-300 underline font-semibold">Upload</router-link> to upload photos over Wi-Fi without cables.
      </div>
    </div>

    <!-- Folder Import Form -->
    <div class="card p-5 space-y-4 bg-ink-900/80 border-white/5 shadow-md">
      <div>
        <label class="block text-xs font-semibold text-gray-300 mb-1.5">Server Directory Path</label>
        <input
          v-model="folderPath"
          type="text"
          placeholder="C:\Users\You\Pictures\CameraDump"
          class="input font-mono text-xs py-2.5"
        />
      </div>

      <label class="flex items-center gap-2 text-xs text-gray-300 cursor-pointer select-none">
        <input v-model="recursive" type="checkbox" class="accent-brand-500 rounded" />
        <span>Scan subdirectories recursively</span>
      </label>

      <button
        class="btn-primary w-full py-2.5 text-xs font-semibold shadow-glow"
        :disabled="!folderPath.trim() || loading"
        @click="runImport"
      >
        <Spinner v-if="loading" :size="16" />
        {{ loading ? 'Scanning & Importing…' : '📥 Start Folder Import' }}
      </button>

      <!-- Live progress -->
      <div v-if="job && job.status !== 'done'" class="space-y-1.5 pt-2">
        <div class="flex justify-between text-xs text-gray-400">
          <span>{{ job.status === 'error' ? 'Failed' : 'Importing & indexing photos…' }}</span>
          <span v-if="job.percent != null" class="font-mono">{{ job.processed }} / {{ job.total }} ({{ job.percent }}%)</span>
        </div>
        <ProgressBar :value="job.percent ?? 5" :active="job.status !== 'error'" />
      </div>
    </div>

    <!-- Result summary -->
    <div v-if="result" class="card p-5 space-y-4 bg-ink-900/80 border-white/5 shadow-md">
      <h2 class="font-bold text-sm" :class="result.failed ? 'text-amber-400' : 'text-emerald-400'">
        {{ result.failed ? 'Import Complete — Some files need retry' : '🎉 Import Complete' }}
      </h2>

      <div class="grid gap-2.5 text-center text-xs" :class="result.failed ? 'grid-cols-4' : 'grid-cols-3'">
        <div class="bg-ink-850 rounded-xl p-3 border border-white/5">
          <div class="text-xl font-bold font-mono text-emerald-400">{{ result.imported }}</div>
          <div class="text-[11px] text-gray-400 mt-0.5">Imported</div>
        </div>
        <div class="bg-ink-850 rounded-xl p-3 border border-white/5">
          <div class="text-xl font-bold font-mono text-gray-300">{{ result.skipped }}</div>
          <div class="text-[11px] text-gray-400 mt-0.5">Already in DB</div>
        </div>
        <div v-if="result.failed" class="bg-red-950/40 border border-red-500/20 rounded-xl p-3">
          <div class="text-xl font-bold font-mono text-red-400">{{ result.failed }}</div>
          <div class="text-[11px] text-gray-400 mt-0.5">Failed</div>
        </div>
        <div class="bg-ink-850 rounded-xl p-3 border border-white/5">
          <div class="text-xl font-bold font-mono text-amber-400">{{ result.duplicates_found }}</div>
          <div class="text-[11px] text-gray-400 mt-0.5">Duplicates</div>
        </div>
      </div>

      <router-link to="/" class="btn-primary w-full text-center text-xs py-2.5 block">View in Library →</router-link>
    </div>

    <div v-if="error" class="card p-4 border border-rose-500/40 bg-rose-950/20 text-rose-300 text-xs">
      <p>{{ error }}</p>
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
