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
        class="btn-danger text-sm"
        @click="cullAll"
      >✂️ Cull all (keep best of each)</button>
    </div>

    <div v-if="loading" class="space-y-6">
      <div v-for="i in 2" :key="i" class="card p-4 space-y-3">
        <Skeleton width="6rem" height="0.7rem" />
        <div class="grid grid-cols-5 gap-2">
          <div v-for="j in 5" :key="j" class="skeleton aspect-square rounded-xl" />
        </div>
      </div>
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

    <EmptyState
      v-else
      icon="📸"
      title="No bursts found"
      subtitle="Burst sequences are detected during a library analysis."
    >
      <template #action>
        <router-link to="/cleanup" class="btn-soft text-sm">✨ Run Analyze</router-link>
      </template>
    </EmptyState>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { photosApi } from '../api/photos'
import Skeleton from '../components/ui/Skeleton.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import { useToast } from '../composables/useToast'
import { useConfirm } from '../composables/useConfirm'

const { success } = useToast()
const { confirm } = useConfirm()

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
  success(`Culled ${ids.length} shot${ids.length > 1 ? 's' : ''}`)
}

async function cullAll() {
  const allIds = groups.value.flatMap((g) => [...(checked[g.burst_id] ?? [])])
  if (!allIds.length) return
  const ok = await confirm({
    title: `Cull ${allIds.length} photos?`,
    message: 'The sharpest shot in each burst is kept. The rest go to Trash.',
    confirmText: 'Cull bursts',
    danger: true,
  })
  if (!ok) return
  await photosApi.bulkDelete(allIds)
  success(`Culled ${allIds.length} photos`)
  await load()
}

function cols(n) {
  return { gridTemplateColumns: `repeat(${Math.min(n, 5)}, minmax(0, 1fr))` }
}
</script>
