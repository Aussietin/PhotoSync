import axios from 'axios'
import { auth, signalAuthRequired, clearToken } from '../auth'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  if (auth.token) config.headers['X-API-Token'] = auth.token
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      clearToken()
      signalAuthRequired()
    }
    return Promise.reject(err)
  },
)

export const photosApi = {
  list: (params) => api.get('/photos', { params }),
  get: (id) => api.get(`/photos/${id}`),
  upload: (files, onProgress) => {
    const form = new FormData()
    files.forEach((f) => form.append('files', f))
    return api.post('/photos/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: onProgress,
    })
  },
  delete: (id) => api.delete(`/photos/${id}`),
  permanentDelete: (id) => api.delete(`/photos/${id}/permanent`),
  restore: (id) => api.post(`/photos/${id}/restore`),
  toggleFavorite: (id) => api.post(`/photos/${id}/favorite`),
  updateNotes: (id, notes) => api.patch(`/photos/${id}/notes`, { notes }),
  timeline: () => api.get('/photos/timeline'),
  duplicates: () => api.get('/photos/duplicates'),
  trash: () => api.get('/photos/trash'),
  map: () => api.get('/photos/map'),
  downloadZip: (photo_ids) =>
    api.post('/photos/download-zip', { photo_ids }, { responseType: 'blob' }),
  importFolder: (path, recursive = true) =>
    api.post('/photos/import-folder', { path, recursive }),
  bulkDelete: (photo_ids) => api.post('/photos/bulk/delete', { photo_ids }),
  bulkFavorite: (photo_ids) => api.post('/photos/bulk/favorite', { photo_ids }),
  bulkRestore: (photo_ids) => api.post('/photos/bulk/restore', { photo_ids }),

  // Screenshot detection
  listScreenshots: (params) => api.get('/photos/screenshots', { params }),
  scanScreenshots: () => api.post('/photos/scan-screenshots'),

  // Duplicate groups (returns { job_id } — poll via jobsApi)
  duplicateGroups: () => api.get('/photos/duplicate-groups'),
  rescanDuplicates: () => api.post('/photos/rescan-duplicates'),

  // Burst groups
  burstGroups: () => api.get('/photos/burst-groups'),

  // Triage
  triageQueue: (params) => api.get('/photos/triage-queue', { params }),

  // Mass cleanup
  cleanupSummary: (max_quality = 0.3) =>
    api.get('/photos/cleanup-summary', { params: { max_quality } }),
  runCleanup: (filters) => api.post('/photos/cleanup', filters),
  cleanupHistory: () => api.get('/photos/cleanup-history'),
  undoCleanup: (batch) => api.post(`/photos/undo-cleanup/${batch}`),
  emptyTrash: (older_than_days = null) =>
    api.post('/photos/empty-trash', null, {
      params: older_than_days == null ? {} : { older_than_days },
    }),

  // Background jobs (import / analyze / rescan return { job_id })
  analyzeLibrary: (recompute_quality = true) =>
    api.post('/photos/analyze', null, { params: { recompute_quality } }),
}

export const jobsApi = {
  list: () => api.get('/jobs'),
  get: (id) => api.get(`/jobs/${id}`),
}

export const exportApi = {
  keepersUrl: (opts = {}) => {
    const p = new URLSearchParams(
      auth.token ? { ...opts, token: auth.token } : opts,
    ).toString()
    return `/api/export/keepers${p ? `?${p}` : ''}`
  },
  deletionPlanUrl: (fmt = 'csv') => {
    const p = new URLSearchParams(
      auth.token ? { fmt, token: auth.token } : { fmt },
    ).toString()
    return `/api/export/deletion-plan?${p}`
  },
}

export const tagsApi = {
  list: () => api.get('/tags'),
  add: (photoId, name) => api.post(`/tags/${photoId}`, { name }),
  remove: (tagId) => api.delete(`/tags/${tagId}`),
}

export const searchApi = {
  search: (params) => api.get('/search', { params }),
}

export const albumsApi = {
  list: () => api.get('/albums'),
  create: (name, description) => api.post('/albums', { name, description }),
  get: (id) => api.get(`/albums/${id}`),
  update: (id, name, description) => api.patch(`/albums/${id}`, { name, description }),
  delete: (id) => api.delete(`/albums/${id}`),
  addPhotos: (id, photo_ids) => api.post(`/albums/${id}/photos`, { photo_ids }),
  removePhoto: (albumId, photoId) => api.delete(`/albums/${albumId}/photos/${photoId}`),
  setCover: (albumId, photoId) => api.patch(`/albums/${albumId}/cover/${photoId}`),
}

export const statsApi = {
  get: () => api.get('/stats'),
}
