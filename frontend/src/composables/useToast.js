import { ref } from 'vue'

// Shared, app-wide toast queue (module singleton)
const toasts = ref([])
let seq = 0

function dismiss(id) {
  toasts.value = toasts.value.filter((t) => t.id !== id)
}

function push(message, { type = 'info', timeout = 3500, action = null } = {}) {
  const id = ++seq
  toasts.value.push({ id, message, type, action })
  if (timeout > 0) setTimeout(() => dismiss(id), timeout)
  return id
}

export function useToast() {
  return {
    toasts,
    dismiss,
    toast: (msg, opts) => push(msg, opts),
    success: (msg, opts) => push(msg, { ...opts, type: 'success' }),
    error: (msg, opts) => push(msg, { ...opts, type: 'error', timeout: 5000 }),
    info: (msg, opts) => push(msg, { ...opts, type: 'info' }),
  }
}
