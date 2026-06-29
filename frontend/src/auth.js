import { reactive } from 'vue'

const TOKEN_KEY = 'photosync_token'

export const auth = reactive({
  token: localStorage.getItem(TOKEN_KEY) || '',
  required: false, // set true when server returns 401
})

export function setToken(t) {
  auth.token = t.trim()
  auth.required = false
  if (auth.token) localStorage.setItem(TOKEN_KEY, auth.token)
  else localStorage.removeItem(TOKEN_KEY)
}

export function clearToken() {
  auth.token = ''
  localStorage.removeItem(TOKEN_KEY)
}

export function signalAuthRequired() {
  auth.required = true
}
