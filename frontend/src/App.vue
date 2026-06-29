<template>
  <div class="flex flex-col min-h-screen">
    <!-- Top nav -->
    <header class="sticky top-0 z-50 bg-ink-950/70 backdrop-blur-xl border-b border-white/5">
      <div class="max-w-screen-xl mx-auto px-4 h-14 flex items-center gap-2">
        <router-link to="/" class="flex items-center gap-2 flex-shrink-0 group">
          <span class="relative grid place-items-center w-8 h-8 rounded-xl bg-brand-gradient shadow-glow">
            <svg class="text-white" width="18" height="18" viewBox="0 0 24 24" fill="none">
              <path d="M3 7a2 2 0 0 1 2-2h2l1.5-2h7L19 5h0a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
              <circle cx="12" cy="12.5" r="3.2" stroke="currentColor" stroke-width="1.8"/>
            </svg>
          </span>
          <span class="text-lg font-extrabold tracking-tight text-gradient">PhotoSync</span>
        </router-link>

        <!-- Desktop nav -->
        <nav class="hidden sm:flex items-center gap-0.5 flex-1 justify-center">
          <NavLink v-for="item in primaryNav" :key="item.to" :to="item.to" :icon="item.icon">
            {{ item.label }}
          </NavLink>
          <NavMenu />
        </nav>

        <div class="flex items-center gap-2 flex-shrink-0 ml-auto sm:ml-0">
          <router-link to="/upload" class="btn-primary text-sm py-1.5 px-3 hidden sm:flex">
            <span class="text-base leading-none">＋</span> Upload
          </router-link>
          <!-- QR connect -->
          <button
            class="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 border border-white/5 text-gray-300 text-sm font-medium transition-colors"
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
      <router-view v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </router-view>
    </main>

    <!-- Mobile bottom nav -->
    <nav class="sm:hidden fixed bottom-0 inset-x-0 z-50 bg-ink-950/85 backdrop-blur-xl border-t border-white/5">
      <div class="relative grid grid-cols-5 h-16 items-center">
        <BottomTab to="/" icon="🖼️" label="Library" />
        <BottomTab to="/triage" icon="🃏" label="Triage" />

        <!-- Floating primary action -->
        <div class="flex justify-center">
          <router-link
            to="/cleanup"
            class="relative -translate-y-4 w-14 h-14 rounded-2xl bg-brand-gradient shadow-glow grid place-items-center text-2xl active:scale-95 transition-transform"
          >
            <span class="absolute inset-0 rounded-2xl bg-brand-400/40 animate-pulse-ring" />
            <span class="relative">✨</span>
          </router-link>
        </div>

        <BottomTab to="/search" icon="🔍" label="Search" />
        <button
          class="flex flex-col items-center justify-center gap-0.5 text-[11px] font-medium text-gray-500 hover:text-gray-300 transition-colors"
          @click="showMore = true"
        >
          <span class="text-xl leading-none">⋯</span>
          <span>More</span>
        </button>
      </div>
    </nav>

    <div class="sm:hidden h-16" />

    <MobileMore :open="showMore" @close="showMore = false" />
    <ConnectModal v-if="showConnect" @close="showConnect = false" />

    <!-- Global overlays -->
    <ToastHost />
    <ConfirmHost />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import NavLink from './components/NavLink.vue'
import NavMenu from './components/NavMenu.vue'
import BottomTab from './components/BottomTab.vue'
import MobileMore from './components/MobileMore.vue'
import ConnectModal from './components/ConnectModal.vue'
import ToastHost from './components/ui/ToastHost.vue'
import ConfirmHost from './components/ui/ConfirmHost.vue'
import { primaryNav } from './nav'

const showConnect = ref(false)
const showMore = ref(false)
</script>
