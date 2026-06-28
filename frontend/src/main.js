import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './style.css'

import HomeView from './views/HomeView.vue'
import TimelineView from './views/TimelineView.vue'
import SearchView from './views/SearchView.vue'
import UploadView from './views/UploadView.vue'
import DuplicatesView from './views/DuplicatesView.vue'
import AlbumsView from './views/AlbumsView.vue'
import AlbumDetailView from './views/AlbumDetailView.vue'
import StatsView from './views/StatsView.vue'
import MapView from './views/MapView.vue'
import TrashView from './views/TrashView.vue'
import ImportView from './views/ImportView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView },
    { path: '/timeline', component: TimelineView },
    { path: '/search', component: SearchView },
    { path: '/upload', component: UploadView },
    { path: '/duplicates', component: DuplicatesView },
    { path: '/albums', component: AlbumsView },
    { path: '/albums/:id', component: AlbumDetailView },
    { path: '/stats', component: StatsView },
    { path: '/map', component: MapView },
    { path: '/trash', component: TrashView },
    { path: '/import', component: ImportView },
  ],
})

createApp(App).use(router).mount('#app')
