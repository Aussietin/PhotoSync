import { ref } from 'vue'

// Shared confirm-dialog state (module singleton)
const state = ref(null)
let resolver = null

/**
 * Open a styled confirmation dialog. Returns a promise that resolves
 * to true (confirmed) or false (cancelled).
 *
 *   const ok = await confirm({ title, message, confirmText, danger })
 */
function confirm(opts = {}) {
  state.value = {
    title: opts.title || 'Are you sure?',
    message: opts.message || '',
    icon: opts.icon || (opts.danger ? '🗑️' : '❓'),
    confirmText: opts.confirmText || 'Confirm',
    cancelText: opts.cancelText || 'Cancel',
    danger: opts.danger ?? false,
  }
  return new Promise((resolve) => {
    resolver = resolve
  })
}

function resolve(result) {
  state.value = null
  resolver?.(result)
  resolver = null
}

export function useConfirm() {
  return { confirm, state, resolve }
}
