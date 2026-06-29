<template>
  <div class="fixed inset-0 z-[100] flex items-center justify-center bg-gray-950 p-4">
    <div class="w-full max-w-sm space-y-6">
      <!-- Icon + heading -->
      <div class="text-center space-y-3">
        <div class="text-5xl">🔒</div>
        <h1 class="text-xl font-bold">Access token required</h1>
        <p class="text-sm text-gray-400 leading-relaxed">
          This PhotoSync server is protected. Enter the token from
          <span class="font-mono text-xs bg-gray-800 px-1.5 py-0.5 rounded">backend/.env</span>
          to continue.
        </p>
      </div>

      <!-- Input -->
      <div class="card p-5 space-y-4">
        <div>
          <label class="block text-xs text-gray-500 mb-1.5">Access token</label>
          <input
            v-model="input"
            type="password"
            placeholder="Paste your token here"
            autocomplete="off"
            class="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-2.5 text-sm font-mono focus:outline-none focus:border-brand-500"
            @keydown.enter="connect"
          />
        </div>

        <button
          class="btn-primary w-full"
          :disabled="!input.trim() || checking"
          @click="connect"
        >
          {{ checking ? 'Checking…' : 'Connect' }}
        </button>

        <p v-if="error" class="text-xs text-red-400 text-center">{{ error }}</p>
      </div>

      <!-- Help -->
      <div class="text-center text-xs text-gray-600 space-y-1">
        <p>
          Don't have a token? Add
          <span class="font-mono bg-gray-800 px-1.5 py-0.5 rounded">API_TOKEN=…</span>
          to <span class="font-mono">backend/.env</span> and restart the server.
        </p>
        <p>
          Generate one:
          <span class="font-mono bg-gray-800 px-1.5 py-0.5 rounded select-all">python -c "import secrets; print(secrets.token_urlsafe(32))"</span>
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import axios from 'axios'
import { setToken } from '../auth'

const input = ref('')
const checking = ref(false)
const error = ref(null)

async function connect() {
  if (!input.value.trim()) return
  checking.value = true
  error.value = null
  try {
    await axios.get('/api/stats', {
      headers: { 'X-API-Token': input.value.trim() },
    })
    setToken(input.value.trim())
  } catch (e) {
    if (e.response?.status === 401) {
      error.value = 'Token not accepted. Check it matches your server .env.'
    } else {
      // Server error / offline — token format might be fine, save anyway
      error.value = `Server error (${e.response?.status ?? 'no response'}). Token saved — reload to retry.`
      setToken(input.value.trim())
    }
  } finally {
    checking.value = false
  }
}
</script>
