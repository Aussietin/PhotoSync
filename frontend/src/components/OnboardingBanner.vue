<template>
  <div v-if="visible" class="card p-5 mb-5 border border-brand-500/30 bg-brand-500/5 relative">
    <button
      class="absolute top-3 right-3 text-gray-500 hover:text-gray-300 text-sm"
      title="Dismiss"
      @click="dismiss"
    >✕</button>

    <h2 class="font-semibold text-gray-100 mb-1">How PhotoSync works</h2>
    <p class="text-xs text-gray-500 mb-4 max-w-xl">
      Apple doesn't let any web app delete photos from your iPhone — so nothing here
      ever touches your camera roll. Uploading/importing only <em>copies</em> photos to
      this PC. To actually free up space on your phone, follow all four steps below.
    </p>

    <ol class="space-y-3 text-sm">
      <li class="flex gap-3">
        <span class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-500/20 text-brand-300 text-xs font-bold grid place-items-center">1</span>
        <span class="text-gray-300">
          <router-link to="/upload" class="text-brand-300 hover:underline font-medium">Upload</router-link>
          a batch from your phone's browser, or
          <router-link to="/import" class="text-brand-300 hover:underline font-medium">Import</router-link>
          a folder. Your phone keeps every original — this only copies them here.
        </span>
      </li>
      <li class="flex gap-3">
        <span class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-500/20 text-brand-300 text-xs font-bold grid place-items-center">2</span>
        <span class="text-gray-300">
          Run <router-link to="/cleanup" class="text-brand-300 hover:underline font-medium">Cleanup → Analyze</router-link>,
          then trash junk (screenshots, duplicates, blur, large videos) and cull
          <router-link to="/people" class="text-brand-300 hover:underline font-medium">People</router-link> you don't recognise.
          Everything goes to Trash first — nothing is gone for good yet.
          <br />
          <span class="text-xs text-amber-300/90">
            ♥ Tip: tap the heart on any photo (e.g. a screenshot with a password) to Favorite
            it — favorites are never touched by any bulk cleanup, ever.
          </span>
        </span>
      </li>
      <li class="flex gap-3">
        <span class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-500/20 text-brand-300 text-xs font-bold grid place-items-center">3</span>
        <span class="text-gray-300">
          <router-link to="/export" class="text-brand-300 hover:underline font-medium">Export → Download keepers ZIP</router-link>
          — this becomes your clean archive (and eventually your NAS backup).
        </span>
      </li>
      <li class="flex gap-3">
        <span class="flex-shrink-0 w-6 h-6 rounded-full bg-brand-500/20 text-brand-300 text-xs font-bold grid place-items-center">4</span>
        <span class="text-gray-300">
          <span class="font-medium text-gray-200">This is the step that actually clears your phone:</span>
          on the <router-link to="/export" class="text-brand-300 hover:underline font-medium">Export</router-link> page,
          download the <em>deletion plan</em> and use the built-in iOS Shortcut recipe to
          delete exactly the culled photos from your camera roll, one tap.
        </span>
      </li>
    </ol>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const KEY = 'photosync_onboarding_dismissed'
const visible = ref(localStorage.getItem(KEY) !== '1')

function dismiss() {
  localStorage.setItem(KEY, '1')
  visible.value = false
}
</script>
