<template>
  <div class="max-w-2xl mx-auto space-y-6">
    <div>
      <h1 class="text-xl font-bold">Export</h1>
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
        <a :href="csvHref" class="btn-ghost text-sm">⬇ CSV</a>
        <a :href="jsonHref" class="btn-ghost text-sm">⬇ JSON</a>
      </div>
    </div>

    <!-- Workflow guidance -->
    <div class="card p-5 space-y-2">
      <h2 class="font-semibold">Recommended workflow</h2>
      <ol class="text-sm text-gray-400 space-y-1.5 list-decimal list-inside">
        <li>Dump your full camera roll to a folder (Finder / Image Capture / iCloud download), then <router-link to="/import" class="text-brand-400 hover:underline">Import</router-link> it.</li>
        <li>Run <router-link to="/cleanup" class="text-brand-400 hover:underline">Smart Cleanup</router-link> and <router-link to="/triage" class="text-brand-400 hover:underline">Triage</router-link> to send junk to Trash.</li>
        <li>Download the keepers ZIP above — this becomes your clean master archive.</li>
        <li>On the phone: use the deletion plan to remove the culled photos (or wipe the roll and re-sync the keepers).</li>
      </ol>
      <p class="text-xs text-gray-600 pt-1">
        Note: deleting from the iOS camera roll requires the Photos app or an iOS Shortcut —
        no web app (including this one) can do it for you.
      </p>
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
