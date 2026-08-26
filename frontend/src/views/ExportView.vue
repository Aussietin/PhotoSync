<template>
  <div class="max-w-2xl mx-auto space-y-6">
    <div class="bg-ink-900/60 p-5 rounded-2xl border border-white/5 backdrop-blur-md">
      <h1 class="text-xl font-extrabold tracking-tight text-white flex items-center gap-2">
        <span>Export Library & Keepers</span>
      </h1>
      <p class="text-xs text-gray-400 mt-1">
        Export your organized keeper library or download deletion plans to sync culls back to devices.
      </p>
    </div>

    <!-- Keepers export -->
    <div class="card p-5 space-y-4 bg-ink-900/80 border-white/5 shadow-md">
      <div>
        <h2 class="font-bold text-sm text-gray-100 flex items-center gap-2">
          <span>📦</span> Download Keepers Archive
        </h2>
        <p class="text-xs text-gray-400 mt-1">
          A clean ZIP of your live, non-duplicate photos organised into Year/Month subfolders. Streamed on-the-fly from disk.
        </p>
      </div>

      <div class="space-y-2 text-xs text-gray-300">
        <label class="flex items-center gap-2 cursor-pointer select-none">
          <input v-model="excludeScreenshots" type="checkbox" class="accent-brand-500 rounded" />
          <span>Exclude screenshots from ZIP</span>
        </label>
        <label class="flex items-center gap-2 cursor-pointer select-none">
          <input v-model="excludeLowQuality" type="checkbox" class="accent-brand-500 rounded" />
          <span>Exclude low-quality / blurry frames</span>
        </label>
      </div>

      <a :href="keepersHref" class="btn-primary inline-flex text-xs py-2.5 px-4 font-semibold shadow-glow">
        ⬇ Download Keepers ZIP
      </a>
    </div>

    <!-- Deletion plan -->
    <div class="card p-5 space-y-3 bg-ink-900/80 border-white/5 shadow-md">
      <div>
        <h2 class="font-bold text-sm text-gray-100 flex items-center gap-2">
          <span>📋</span> Device Deletion Plan
        </h2>
        <p class="text-xs text-gray-400 mt-1">
          Structured list of culled photos currently in Trash (filename + reason) to delete matching shots from your phone with an iOS Shortcut.
        </p>
      </div>
      <div class="flex gap-2">
        <a :href="csvHref" class="btn-ghost text-xs py-2 px-3">⬇ Download CSV</a>
        <a :href="jsonHref" class="btn-ghost text-xs py-2 px-3">⬇ Download JSON</a>
      </div>
    </div>

    <!-- Recommended Workflow Card -->
    <div class="card p-5 space-y-3 bg-ink-900/80 border-white/5 text-xs shadow-md">
      <h2 class="font-bold text-gray-100 flex items-center gap-2">
        <span>✨</span> Recommended Culling & Archiving Workflow
      </h2>
      <ol class="text-gray-300 space-y-2 list-decimal list-inside">
        <li>Transfer or import your camera roll to PhotoSync.</li>
        <li>Run <router-link to="/cleanup" class="text-brand-300 underline font-medium">Smart Cleanup</router-link> & <router-link to="/triage" class="text-brand-300 underline font-medium">Triage</router-link> to review and queue clutter for Trash.</li>
        <li>Download the keepers ZIP archive above — this is your permanent clean master library.</li>
        <li>On iPhone: run the deletion plan Shortcut below to free up GBs on your phone.</li>
      </ol>
    </div>

    <!-- iOS Shortcut Recipe -->
    <div class="card p-5 space-y-3 bg-ink-900/80 border-white/5 shadow-md text-xs">
      <h2 class="font-bold text-gray-100 flex items-center gap-2">
        <span>📱</span> iOS Shortcut Recipe — Delete From Camera Roll
      </h2>
      <p class="text-gray-400">
        Build this iOS Shortcut once; tap it anytime on your iPhone to execute the deletion plan CSV directly.
      </p>

      <ol class="text-gray-300 space-y-2 list-decimal list-inside">
        <li>Download the CSV deletion plan and save to <strong>Files → iCloud Drive</strong>.</li>
        <li>Open <strong>Shortcuts</strong> on your iPhone → tap <strong>+</strong> to create a new shortcut.</li>
        <li>Add action: <code>Get File</code> → pick the deletion plan CSV.</li>
        <li>Add action: <code>Split Text</code> by New Lines.</li>
        <li>Add action: <code>Repeat with Each</code>: filter by filename column and call <code>Delete Photos</code>.</li>
      </ol>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { exportApi } from '../api/photos'

const excludeScreenshots = ref(true)
const excludeLowQuality = ref(false)

const keepersHref = computed(() =>
  exportApi.keepersUrl({
    exclude_screenshots: excludeScreenshots.value,
    exclude_low_quality: excludeLowQuality.value,
  })
)
const csvHref = exportApi.deletionPlanUrl('csv')
const jsonHref = exportApi.deletionPlanUrl('json')
</script>
