<template>
  <div>
    <div class="flex items-center justify-between mb-5">
      <div>
        <h1 class="text-xl font-bold">
          Bursts <span class="text-gray-500 font-normal text-base">({{ groups.length }})</span>
        </h1>
        <p class="text-xs text-gray-500 mt-0.5">Runs of near-identical shots — sharpest is kept, the rest pre-checked</p>
      </div>
      <button
        v-if="groups.length"
        class="btn-ghost text-sm text-red-400 hover:text-red-300"
        @click="cullAll"
      >Cull all (keep best of each)</button>
    </div>

    <div v-if="loading" class="flex justify-center py-20">
      <span class="text-gray-500 animate-pulse">Loading…</span>
    </div>

    <div v-else-if="groups.length" class="space-y-6">
      <div v-for="group in groups" :key="group.burst_id" class="card p-4">
        <div class="flex items-center justify-between mb-3">
          <span class="text-xs text-gray-500 font-medium uppercase tracking-wider">
            {{ group.photos.length }} shots
          </span>
          <button class="text-xs text-red-400 hover:text-red-300" @click="cullGroup(group)">Cull checked</button>
        </div>

        <div class="grid gap-2" :style="cols(group.photos.length)">
          <div v-for="p in group.photos" :key="p.id" class="relative">
            <div
              class="aspect-square bg-gray-800 rounded-xl overflow-hidden cursor-pointer transition-all"
              :class="p.id === group.keep_id
                ? 'ring-2 ring-green-500'
                : (checkedFor(group).has(p.id) ? 'ring-2 ring-red-500' : 'ring-1 ring-gray-700')"
              @click="p.id === group.keep_id ? null : toggle(group, p.id)"
            >
              <img v-if="p.thumbnail_url" :src="p.thumbnail_url" class="w-full h-full object-cover"
                   :class="checkedFor(group).has(p.id) && 'opacity-60'" />
            </div>
            <div class="mt-1 text-center">
              <span v-if="p.id === group.keep_id" class="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">Keep (best)</span>
              <span v-else
                class="text-xs px-2 py-0.5 rounded-full cursor-pointer"
                :class="checkedFor(group).has(p.id) ? 'bg-red-500/20 text-red-400' : 'bg-gray-700 text-gray-400'"
                @click="toggle(group, p.id)"
              >{{ checkedFor(group).has(p.id) ? 'Delete' : 'Keep' }}</span>
            </div>
            <div class="text-xs text-gray-500 text-center mt-0.5">
              {{ p.quality_score != null ? Math.round(p.quality_score * 100) + '%' : '' }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="flex flex-col items-center py-20 text-gray-600">
      <span class="text-5xl mb-4">📸</span>
      <p>No bursts found.</p>
      <p class="text-sm mt-1">Run <router-link to="/cleanup" class="text-brand-400 hover:underline">Analyze</router-link> to detect them.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { photosApi } from '../api/photos'

const groups = ref([])
const loading = ref(false)
const checked = reactive({})

onMounted(load)

async function load() {
  loading.value = true
  try {
    const { data } = await photosApi.burstGroups()
    groups.value = data.groups
    for (const g of data.groups) checked[g.burst_id] = new Set(g.suggested_delete_ids)
  } finally {
    loading.value = false
  }
}

function checkedFor(group) {
  return checked[group.burst_id] ?? new Set()
}

function toggle(group, id) {
  const s = new Set(checked[group.burst_id] ?? [])
  s.has(id) ? s.delete(id) : s.add(id)
  checked[group.burst_id] = s
}

async function cullGroup(group) {
  const ids = [...(checked[group.burst_id] ?? [])]
  if (!ids.length) return
  await photosApi.bulkDelete(ids)
  groups.value = groups.value
    .map((g) => g.burst_id === group.burst_id
      ? { ...g, photos: g.photos.filter((p) => !ids.includes(p.id)) }
      : g)
    .filter((g) => g.photos.length > 1)
}

async function cullAll() {
  const allIds = groups.value.flatMap((g) => [...(checked[g.burst_id] ?? [])])
  if (!allIds.length) return
  if (!confirm(`Cull ${allIds.length} photos, keeping the best of each burst?`)) return
  await photosApi.bulkDelete(allIds)
  await load()
}

function cols(n) {
  return { gridTemplateColumns: `repeat(${Math.min(n, 5)}, minmax(0, 1fr))` }
}
</script>
