<template>
  <Teleport to="body">
    <div
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
      @click.self="$emit('close')"
    >
      <div class="card max-w-sm w-full p-6 text-center space-y-4">
        <div class="flex items-center justify-between mb-1">
          <h2 class="text-lg font-semibold">Connect your phone</h2>
          <button
            class="w-8 h-8 flex items-center justify-center rounded-full hover:bg-gray-800 text-gray-400"
            @click="$emit('close')"
          >✕</button>
        </div>

        <p class="text-sm text-gray-400">
          Make sure your phone is on the same Wi-Fi network, then scan this QR code to open PhotoSync.
        </p>

        <!-- QR code canvas -->
        <div class="flex justify-center">
          <div class="bg-white p-3 rounded-2xl inline-block">
            <canvas ref="canvas" />
          </div>
        </div>

        <!-- URL display -->
        <div class="bg-gray-800 rounded-xl px-4 py-2 text-sm font-mono text-brand-400 break-all select-all">
          {{ url }}
        </div>

        <p v-if="loading" class="text-xs text-gray-500 animate-pulse">Detecting local IP…</p>
        <p v-if="error" class="text-xs text-red-400">{{ error }}</p>

        <p class="text-xs text-gray-600">
          Or type the URL above into Safari on your iPhone.
        </p>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import QRCode from 'qrcode'
import axios from 'axios'

defineEmits(['close'])

const canvas = ref(null)
const url = ref(window.location.origin)
const loading = ref(true)
const error = ref(null)

onMounted(async () => {
  // Try to get the server's local network IP for a cross-device URL
  try {
    const { data } = await axios.get('/api/server-info')
    const ip = data.local_ips?.[0]
    const port = data.frontend_port ?? 5173
    if (ip && ip !== 'localhost') {
      url.value = `http://${ip}:${port}`
    }
  } catch {
    error.value = 'Could not detect local IP — use the URL shown above.'
  } finally {
    loading.value = false
  }

  // Render QR code onto canvas
  await QRCode.toCanvas(canvas.value, url.value, {
    width: 220,
    margin: 1,
    color: { dark: '#000000', light: '#ffffff' },
    errorCorrectionLevel: 'M',
  })
})
</script>
