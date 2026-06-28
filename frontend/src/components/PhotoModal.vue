<template>
  <Teleport to="body">
    <div
      v-if="photo"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
      @click.self="$emit('close')"
    >
      <div class="card max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <!-- Image -->
        <div class="relative bg-black flex items-center justify-center" style="max-height: 60vh">
          <img
            :src="photo.original_url"
            :alt="photo.filename"
            class="max-w-full max-h-[60vh] object-contain"
          />
          <button
            class="absolute top-3 right-3 w-8 h-8 flex items-center justify-center rounded-full bg-black/60 text-white hover:bg-black/80"
            @click="$emit('close')"
          >✕</button>
        </div>

        <!-- Metadata -->
        <div class="p-4 space-y-3">
          <h2 class="font-semibold text-sm text-gray-300 truncate">{{ photo.filename }}</h2>

          <div class="grid grid-cols-2 gap-2 text-xs text-gray-400">
            <div v-if="photo.taken_at"><span class="text-gray-500">Taken</span><br />{{ formatDate(photo.taken_at) }}</div>
            <div v-if="photo.camera"><span class="text-gray-500">Camera</span><br />{{ photo.camera }}</div>
            <div v-if="photo.width"><span class="text-gray-500">Size</span><br />{{ photo.width }}×{{ photo.height }}</div>
            <div><span class="text-gray-500">File</span><br />{{ formatBytes(photo.file_size) }}</div>
          </div>

          <!-- Tags -->
          <div v-if="allTags.length" class="flex flex-wrap gap-1">
            <span
              v-for="tag in allTags"
              :key="tag"
              class="px-2 py-0.5 bg-gray-800 rounded-full text-xs text-gray-300"
            >{{ tag }}</span>
          </div>

          <!-- Actions -->
          <div class="flex gap-2 pt-1">
            <a :href="photo.original_url" download class="btn-ghost text-sm flex-1">⬇ Download</a>
            <button class="btn-ghost text-sm text-red-400 hover:text-red-300" @click="$emit('delete', photo.id)">🗑 Delete</button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ photo: Object })
defineEmits(['close', 'delete'])

const allTags = computed(() => {
  if (!props.photo) return []
  const manual = props.photo.tags?.map((t) => t.name) ?? []
  const ai = props.photo.ai_tags ?? []
  return [...new Set([...manual, ...ai])]
})

function formatDate(iso) {
  return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
}

function formatBytes(b) {
  if (b < 1024) return `${b} B`
  if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`
  return `${(b / 1048576).toFixed(1)} MB`
}
</script>
