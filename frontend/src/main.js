import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './style.css'

import HomeView from './views/HomeView.vue'
import TimelineView from './views/TimelineView.vue'
import SearchView from './views/SearchView.vue'
import UploadView from './views/UploadView.vue'
import DuplicatesView from './views/DuplicatesView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: HomeView },
    { path: '/timeline', component: TimelineView },
    { path: '/search', component: SearchView },
    { path: '/upload', component: UploadView },
    { path: '/duplicates', component: DuplicatesView },
  ],
})

createApp(App).use(router).mount('#app')
