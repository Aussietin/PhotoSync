<template>
  <div
    class="border-2 border-dashed rounded-2xl p-10 text-center transition-colors cursor-pointer"
    :class="dragging ? 'border-brand-500 bg-brand-500/10' : 'border-gray-700 hover:border-gray-500'"
    @dragover.prevent="dragging = true"
    @dragleave="dragging = false"
    @drop.prevent="onDrop"
    @click="fileInput.click()"
  >
    <div class="text-5xl mb-3">📸</div>
    <p class="text-gray-300 font-medium">Drop photos here or tap to browse</p>
    <p class="text-gray-600 text-sm mt-1">JPEG, PNG, HEIC, WebP — up to 50 MB each</p>
    <input ref="fileInput" type="file" multiple accept="image/*" class="hidden" @change="onFileChange" />
  </div>
</template>

<script setup>
import { ref } from 'vue'

const emit = defineEmits(['files'])
const dragging = ref(false)
const fileInput = ref(null)

function onDrop(e) {
  dragging.value = false
  emit('files', [...e.dataTransfer.files])
}

function onFileChange(e) {
  emit('files', [...e.target.files])
  e.target.value = ''
}
</script>
