<template>
  <div
    class="relative border-2 border-dashed rounded-3xl p-10 text-center transition-all cursor-pointer overflow-hidden group"
    :class="dragging ? 'border-brand-400 bg-brand-500/10 scale-[1.01]' : 'border-white/15 hover:border-brand-400/50 hover:bg-white/[0.02]'"
    @dragover.prevent="dragging = true"
    @dragleave="dragging = false"
    @drop.prevent="onDrop"
    @click="fileInput.click()"
  >
    <div
      class="w-20 h-20 mx-auto mb-4 rounded-3xl grid place-items-center text-4xl bg-brand-gradient-soft border border-white/10 transition-transform group-hover:scale-110"
      :class="dragging && 'animate-float'"
    >📸</div>
    <p class="text-gray-200 font-semibold">Drop photos here or tap to browse</p>
    <p class="text-gray-500 text-sm mt-1">JPEG, PNG, HEIC, WebP — up to 50 MB each</p>
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
