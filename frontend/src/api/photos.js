import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

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
