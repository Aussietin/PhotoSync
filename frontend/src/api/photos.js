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
  timeline: () => api.get('/photos/timeline'),
  duplicates: () => api.get('/photos/duplicates'),
}

export const tagsApi = {
  list: () => api.get('/tags'),
  add: (photoId, name) => api.post(`/tags/${photoId}`, { name }),
  remove: (tagId) => api.delete(`/tags/${tagId}`),
}

export const searchApi = {
  search: (params) => api.get('/search', { params }),
}
