<template>
  <div class="flex flex-col min-h-screen">
    <!-- Top nav -->
    <header class="sticky top-0 z-50 bg-gray-950/90 backdrop-blur border-b border-gray-800 safe-top">
      <div class="max-w-screen-xl mx-auto px-4 h-14 flex items-center justify-between">
        <router-link to="/" class="text-lg font-bold text-brand-500 tracking-tight">
          PhotoSync
        </router-link>
        <nav class="hidden sm:flex items-center gap-1">
          <NavLink to="/">Library</NavLink>
          <NavLink to="/timeline">Timeline</NavLink>
          <NavLink to="/search">Search</NavLink>
          <NavLink to="/duplicates">Duplicates</NavLink>
          <router-link to="/upload" class="btn-primary ml-2 text-sm">+ Upload</router-link>
        </nav>
      </div>
    </header>

    <!-- Main content -->
    <main class="flex-1 max-w-screen-xl mx-auto w-full px-4 py-6">
      <router-view />
    </main>

    <!-- Bottom nav (mobile) -->
    <nav class="sm:hidden fixed bottom-0 inset-x-0 bg-gray-950/95 backdrop-blur border-t border-gray-800 safe-bottom">
      <div class="grid grid-cols-5 h-16">
        <BottomTab to="/" icon="🖼️" label="Library" />
        <BottomTab to="/timeline" icon="📅" label="Timeline" />
        <BottomTab to="/upload" icon="⬆️" label="Upload" primary />
        <BottomTab to="/search" icon="🔍" label="Search" />
        <BottomTab to="/duplicates" icon="🔁" label="Dupes" />
      </div>
    </nav>

    <!-- Spacer for mobile bottom nav -->
    <div class="sm:hidden h-16" />
  </div>
</template>

<script setup>
import NavLink from './components/NavLink.vue'
import BottomTab from './components/BottomTab.vue'
</script>
