<template>
  <div class="flex flex-col min-h-screen">
    <!-- Top nav -->
    <header class="sticky top-0 z-50 bg-gray-950/90 backdrop-blur border-b border-gray-800">
      <div class="max-w-screen-xl mx-auto px-4 h-14 flex items-center justify-between gap-2">
        <router-link to="/" class="text-lg font-bold text-brand-500 tracking-tight flex-shrink-0">
          PhotoSync
        </router-link>

        <!-- Desktop nav -->
        <nav class="hidden sm:flex items-center gap-0.5 flex-1 overflow-x-auto">
          <NavLink to="/">Library</NavLink>
          <NavLink to="/cleanup">✨ Cleanup</NavLink>
          <NavLink to="/triage">Triage</NavLink>
          <NavLink to="/screenshots">Screenshots</NavLink>
          <NavLink to="/duplicates">Dupes</NavLink>
          <NavLink to="/bursts">Bursts</NavLink>
          <NavLink to="/albums">Albums</NavLink>
          <NavLink to="/search">Search</NavLink>
          <NavLink to="/timeline">Timeline</NavLink>
          <NavLink to="/map">Map</NavLink>
          <NavLink to="/stats">Stats</NavLink>
          <NavLink to="/import">Import</NavLink>
          <NavLink to="/export">Export</NavLink>
          <NavLink to="/trash">Trash</NavLink>
        </nav>

        <div class="flex items-center gap-2 flex-shrink-0">
          <router-link to="/upload" class="btn-primary text-sm hidden sm:flex">+ Upload</router-link>
          <!-- QR connect -->
          <button
            class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-gray-800 hover:bg-gray-700 text-gray-300 text-sm font-medium transition-colors"
            title="Connect phone"
            @click="showConnect = true"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
              <path d="M3 3h6v6H3V3zm2 2v2h2V5H5zm8-2h6v6h-6V3zm2 2v2h2V5h-2zM3 13h6v6H3v-6zm2 2v2h2v-2H5zm10 0h2v2h-2v-2zm2-2h2v2h-2v-2zm0 4h2v2h-2v-2zm-4 0h2v2h-2v-2zm0-4h2v2h-2v-2z"/>
            </svg>
            <span class="hidden sm:inline">Connect</span>
          </button>
        </div>
      </div>
    </header>

    <!-- Main content -->
    <main class="flex-1 max-w-screen-xl mx-auto w-full px-4 py-6">
      <router-view />
    </main>

    <!-- Mobile bottom nav -->
    <nav class="sm:hidden fixed bottom-0 inset-x-0 bg-gray-950/95 backdrop-blur border-t border-gray-800">
      <div class="grid grid-cols-5 h-16">
        <BottomTab to="/" icon="🖼️" label="Library" />
        <BottomTab to="/triage" icon="🃏" label="Triage" />
        <BottomTab to="/cleanup" icon="✨" label="Cleanup" :primary="true" />
        <BottomTab to="/screenshots" icon="📱" label="Screens" />
        <BottomTab to="/search" icon="🔍" label="Search" />
      </div>
    </nav>

    <div class="sm:hidden h-16" />

    <ConnectModal v-if="showConnect" @close="showConnect = false" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import NavLink from './components/NavLink.vue'
import BottomTab from './components/BottomTab.vue'
import ConnectModal from './components/ConnectModal.vue'

const showConnect = ref(false)
</script>
