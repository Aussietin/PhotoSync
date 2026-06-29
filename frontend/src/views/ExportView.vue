<template>
  <div class="max-w-2xl mx-auto space-y-6">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Export</h1>
      <p class="text-sm text-gray-500 mt-1">
        Get your cleaned library out. PhotoSync can't delete from your iPhone directly,
        so the workflow is: clean here → export the keepers → make this your master → wipe/re-sync the phone.
      </p>
    </div>

    <!-- Keepers export -->
    <div class="card p-5 space-y-4">
      <div>
        <h2 class="font-semibold">Download keepers</h2>
        <p class="text-xs text-gray-500 mt-0.5">
          A ZIP of your live, non-duplicate photos, organised into year/month folders.
          Streamed from disk, so large libraries are fine.
        </p>
      </div>

      <label class="flex items-center gap-2 text-sm text-gray-300 cursor-pointer select-none">
        <input v-model="excludeScreenshots" type="checkbox" class="accent-brand-500" />
        Exclude screenshots
      </label>
      <label class="flex items-center gap-2 text-sm text-gray-300 cursor-pointer select-none">
        <input v-model="excludeLowQuality" type="checkbox" class="accent-brand-500" />
        Exclude low-quality (blurry/dark) photos
      </label>

      <a :href="keepersHref" class="btn-primary inline-flex text-sm">⬇ Download keepers ZIP</a>
    </div>

    <!-- Deletion plan -->
    <div class="card p-5 space-y-3">
      <div>
        <h2 class="font-semibold">Deletion plan</h2>
        <p class="text-xs text-gray-500 mt-0.5">
          A list of everything currently in Trash — filename + reason — so you can delete
          the same photos on your phone (manually or via an iOS Shortcut).
        </p>
      </div>
      <div class="flex gap-2">
        <a :href="csvHref" class="btn-soft text-sm">⬇ CSV</a>
        <a :href="jsonHref" class="btn-soft text-sm">⬇ JSON</a>
      </div>
    </div>

    <!-- Workflow guidance -->
    <div class="card p-5 space-y-2">
      <h2 class="font-semibold">Recommended workflow</h2>
      <ol class="text-sm text-gray-400 space-y-1.5 list-decimal list-inside">
        <li>Dump your full camera roll to a folder (Finder / Image Capture / iCloud download), then <router-link to="/import" class="text-brand-400 hover:underline">Import</router-link> it.</li>
        <li>Run <router-link to="/cleanup" class="text-brand-400 hover:underline">Smart Cleanup</router-link> and <router-link to="/triage" class="text-brand-400 hover:underline">Triage</router-link> to send junk to Trash.</li>
        <li>Download the keepers ZIP above — this becomes your clean master archive.</li>
        <li>On the phone: use the deletion plan + iOS Shortcut below to remove culled photos.</li>
      </ol>
      <p class="text-xs text-gray-600 pt-1">
        Deleting from the iOS camera roll requires the Photos app or an iOS Shortcut —
        no web app (including this one) can do it for you.
      </p>
    </div>

    <!-- iOS Shortcut recipe -->
    <div class="card p-5 space-y-4">
      <div>
        <h2 class="font-semibold">iOS Shortcut — delete from camera roll</h2>
        <p class="text-xs text-gray-500 mt-0.5">
          Build this Shortcut once; tap it on your phone to act on the deletion plan CSV.
        </p>
      </div>

      <ol class="text-sm text-gray-300 space-y-3 list-decimal list-inside marker:text-gray-600">
        <li>
          <span class="font-medium">Download the deletion plan CSV</span> (button above) and
          save it to <span class="font-mono text-xs bg-gray-800 px-1.5 py-0.5 rounded">Files → iCloud Drive</span>
          so your iPhone can find it.
        </li>
        <li>
          Open <span class="font-medium">Shortcuts</span> on your iPhone → tap <span class="font-medium">+</span> to create a new shortcut.
        </li>
        <li>
          Add action: <span class="font-mono text-xs bg-gray-800 px-1.5 py-0.5 rounded">Get File</span>
          → choose the CSV from iCloud Drive.
        </li>
        <li>
          Add action: <span class="font-mono text-xs bg-gray-800 px-1.5 py-0.5 rounded">Split Text</span>
          → separator <span class="font-mono text-xs bg-gray-800 px-1.5 py-0.5 rounded">New Lines</span>.
        </li>
        <li>
          Add action: <span class="font-mono text-xs bg-gray-800 px-1.5 py-0.5 rounded">Repeat with Each</span>
          over the split lines.
          <ul class="mt-1.5 ml-4 space-y-1.5 list-disc marker:text-gray-600">
            <li>Add <span class="font-mono text-xs bg-gray-800 px-1.5 py-0.5 rounded">If</span>: <em>Repeat Item</em> does not contain <span class="font-mono text-xs bg-gray-800 px-1.5 py-0.5 rounded">filename</span> (skip the CSV header row).</li>
            <li>Add <span class="font-mono text-xs bg-gray-800 px-1.5 py-0.5 rounded">Split Text</span>: split <em>Repeat Item</em> by <span class="font-mono text-xs bg-gray-800 px-1.5 py-0.5 rounded">,</span> → get <strong>Item at Index 1</strong> (that's the filename column).</li>
            <li>Add <span class="font-mono text-xs bg-gray-800 px-1.5 py-0.5 rounded">Find Photos</span> where <em>Filename</em> is the split result.</li>
            <li>Add <span class="font-mono text-xs bg-gray-800 px-1.5 py-0.5 rounded">Delete Photos</span> — iOS will ask for permission the first time.</li>
          </ul>
        </li>
        <li>
          Name the shortcut <span class="font-mono text-xs bg-gray-800 px-1.5 py-0.5 rounded">PhotoSync Cull</span> and add it to your home screen for one-tap use.
        </li>
      </ol>

      <div class="text-xs text-gray-600 bg-gray-900/50 rounded-xl p-3 space-y-1">
        <p><strong class="text-gray-500">Tips:</strong></p>
        <p>• The CSV column order is: <span class="font-mono">filename, reason, deleted_at, file_size</span></p>
        <p>• <em>Find Photos</em> matches by original filename — if iOS renamed your photo it may not find it. The archive-and-replace method (sync keepers back to phone) is more reliable.</p>
        <p>• Run Triage or Cleanup first and review Trash before running the Shortcut — once deleted from iOS they go to the <em>Recently Deleted</em> album (30-day recovery window).</p>
      </div>
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
