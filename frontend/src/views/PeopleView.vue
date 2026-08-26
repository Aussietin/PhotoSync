<template>
  <div class="space-y-4">
    <div class="flex flex-wrap items-center justify-between gap-3 bg-ink-900/60 p-4 rounded-2xl border border-white/5 backdrop-blur-md">
      <div>
        <h1 class="text-xl font-extrabold tracking-tight text-white flex items-center gap-2">
          <span>People & Faces</span>
          <span class="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-brand-500/20 text-brand-300 border border-brand-400/20">
            {{ total.toLocaleString() }}
          </span>
        </h1>
        <p class="text-xs text-gray-400 mt-1">
          Faces clustered locally on your device. Name who you know — bulk-cull unknown people.
        </p>
      </div>

      <div class="flex items-center gap-3 flex-wrap text-xs">
        <label class="flex items-center gap-1.5 text-gray-300 cursor-pointer select-none">
          <input v-model="hideOneOffs" type="checkbox" class="accent-brand-500 rounded" @change="load" />
          <span>Hide single appearances</span>
        </label>
      </div>
    </div>

    <!-- Filter chips -->
    <div class="flex items-center gap-1.5 overflow-x-auto no-scrollbar">
      <button
        class="chip"
        :class="filter === 'all' ? 'chip-active' : 'chip-muted'"
        @click="filter = 'all'"
      >
        All ({{ people.length }})
      </button>
      <button
        class="chip"
        :class="filter === 'known' ? 'chip-active text-amber-300 border-amber-500/40 bg-amber-500/20' : 'chip-muted'"
        @click="filter = 'known'"
      >
        ★ Known ({{ knownCount }})
      </button>
      <button
        class="chip"
        :class="filter === 'unnamed' ? 'chip-active text-purple-300 border-purple-500/40 bg-purple-500/20' : 'chip-muted'"
        @click="filter = 'unnamed'"
      >
        Unnamed ({{ unnamedCount }})
      </button>
    </div>

    <PhotoGridSkeleton v-if="loading && !people.length" :count="12" />

    <div v-else-if="filteredPeople.length" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3.5">
      <div
        v-for="p in filteredPeople"
        :key="p.id"
        class="card p-3.5 flex flex-col gap-2.5 bg-ink-900/85 border-white/5 hover:border-white/15 transition-all shadow-md group"
      >
        <router-link :to="`/people/${p.id}`" class="block relative aspect-square rounded-2xl overflow-hidden bg-ink-850 border border-white/5 group-hover:border-brand-500/40 transition-colors">
          <img
            v-if="p.cover_url"
            :src="p.cover_url"
            class="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
          />
          <div v-else class="flex items-center justify-center w-full h-full text-4xl text-gray-600">🙂</div>

          <span
            v-if="p.is_known"
            class="absolute top-2 right-2 w-6 h-6 rounded-full bg-black/60 backdrop-blur-md text-amber-400 flex items-center justify-center text-xs shadow-md border border-white/10"
            title="Known Person"
          >★</span>
        </router-link>

        <input
          :value="p.name || ''"
          placeholder="Name this person…"
          class="input text-xs py-1.5 px-2.5 bg-ink-800/80 font-medium placeholder:text-gray-500"
          @change="rename(p, $event.target.value)"
        />

        <div class="flex items-center justify-between text-xs text-gray-400 px-0.5 pt-0.5">
          <router-link :to="`/people/${p.id}`" class="hover:text-brand-300 font-mono text-[11px]">
            {{ p.photo_count }} photo{{ p.photo_count !== 1 ? 's' : '' }}
          </router-link>
          <button
            class="text-[11px] text-red-400 hover:text-red-300 hover:underline"
            @click="trashAll(p)"
          >
            Trash all
          </button>
        </div>
      </div>
    </div>

    <EmptyState
      v-else
      icon="🙂"
      title="No people identified yet"
      subtitle="Face detection and clustering runs automatically during library analysis."
    >
      <template #action>
        <router-link to="/cleanup" class="btn-primary text-sm">✨ Go to Cleanup → Run Analyze</router-link>
      </template>
    </EmptyState>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { peopleApi } from '../api/photos'
import PhotoGridSkeleton from '../components/ui/PhotoGridSkeleton.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import { useToast } from '../composables/useToast'
import { useConfirm } from '../composables/useConfirm'

const { success } = useToast()
const { confirm } = useConfirm()

const people = ref([])
const total = ref(0)
const loading = ref(false)
const hideOneOffs = ref(false)
const filter = ref('all')

const knownCount = computed(() => people.value.filter((p) => p.is_known).length)
const unnamedCount = computed(() => people.value.filter((p) => !p.name).length)

const filteredPeople = computed(() => {
  if (filter.value === 'known') return people.value.filter((p) => p.is_known)
  if (filter.value === 'unnamed') return people.value.filter((p) => !p.name)
  return people.value
})

async function load() {
  loading.value = true
  try {
    const { data } = await peopleApi.list({ min_photos: hideOneOffs.value ? 2 : 1 })
    people.value = data.people
    total.value = data.total
  } finally {
    loading.value = false
  }
}

async function rename(person, name) {
  const { data } = await peopleApi.update(person.id, { name })
  person.name = data.name
  person.is_known = data.is_known
  success(`Updated name to ${data.name || 'Unnamed'}`)
}

async function trashAll(person) {
  const label = person.name || 'this person'
  const ok = await confirm({
    title: `Trash all ${person.photo_count} photos of ${label}?`,
    message: 'Favorites are kept safe, and photos where a known contact also appears will be automatically skipped.',
    confirmText: 'Move to Trash',
    danger: true,
  })
  if (!ok) return
  const { data } = await peopleApi.trashPhotos(person.id)
  if (data.skipped_mixed) {
    success(`Moved ${data.deleted} to Trash — skipped ${data.skipped_mixed} group photos`)
  } else {
    success(`Moved ${data.deleted} photos to Trash`)
  }
  await load()
}

onMounted(load)
</script>
