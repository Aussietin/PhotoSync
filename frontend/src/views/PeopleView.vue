<template>
  <div>
    <div class="flex flex-wrap items-center gap-3 mb-2">
      <div>
        <h1 class="text-xl font-bold">
          People
          <span class="text-gray-500 font-normal text-base">({{ total }})</span>
        </h1>
        <p class="text-xs text-gray-500 mt-0.5">
          Grouped by face, on your machine. Name who you know — bulk-remove who you don't.
        </p>
      </div>
      <label class="ml-auto flex items-center gap-2 text-xs text-gray-400 cursor-pointer select-none">
        <input type="checkbox" v-model="hideOneOffs" class="accent-brand-500" @change="load" />
        Hide one-offs
      </label>
    </div>

    <PhotoGridSkeleton v-if="loading && !people.length" :count="12" />

    <div v-else-if="people.length" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
      <div v-for="p in people" :key="p.id" class="card p-3 flex flex-col gap-2">
        <router-link :to="`/people/${p.id}`" class="block relative">
          <div class="aspect-square rounded-xl overflow-hidden bg-gray-800">
            <img v-if="p.cover_url" :src="p.cover_url" class="w-full h-full object-cover" />
            <div v-else class="flex items-center justify-center w-full h-full text-3xl text-gray-600">🙂</div>
          </div>
          <span
            v-if="p.is_known"
            class="absolute top-1.5 right-1.5 text-amber-400 text-sm drop-shadow"
            title="Known"
          >★</span>
        </router-link>

        <input
          :value="p.name || ''"
          placeholder="Name this person…"
          class="input text-sm py-1"
          @change="rename(p, $event.target.value)"
        />

        <div class="flex items-center justify-between text-xs text-gray-500">
          <router-link :to="`/people/${p.id}`" class="hover:text-gray-300">
            {{ p.photo_count }} photo{{ p.photo_count !== 1 ? 's' : '' }}
          </router-link>
          <button
            class="text-red-400 hover:text-red-300"
            @click="trashAll(p)"
          >Trash all</button>
        </div>
      </div>
    </div>

    <EmptyState
      v-else
      icon="🙂"
      title="No people found yet"
      subtitle="Run Analyze (with face grouping) from the Cleanup page to detect and group faces."
    >
      <template #action>
        <router-link to="/cleanup" class="btn-primary text-sm">Go to Cleanup → Analyze</router-link>
      </template>
    </EmptyState>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
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
}

async function trashAll(person) {
  const label = person.name || 'this person'
  const ok = await confirm({
    title: `Trash all ${person.photo_count} photos of ${label}?`,
    message: 'Favorites are kept. Everything goes to Trash and can be restored.',
    confirmText: 'Move to Trash',
    danger: true,
  })
  if (!ok) return
  const { data } = await peopleApi.trashPhotos(person.id)
  success(`Moved ${data.deleted} photos to Trash`)
  await load()
}

onMounted(load)
</script>
