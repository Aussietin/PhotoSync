<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3 bg-ink-900/60 p-4 rounded-2xl border border-white/5 backdrop-blur-md">
      <div>
        <h1 class="text-xl font-extrabold tracking-tight text-white flex items-center gap-2">
          <span>Burst Sequences</span>
          <span class="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-brand-500/20 text-brand-300 border border-brand-400/20">
            {{ groups.length }} {{ groups.length === 1 ? 'group' : 'groups' }}
          </span>
        </h1>
        <p class="text-xs text-gray-400 mt-1">
          Rapid shots taken seconds apart — the sharpest photo is kept by default, with lesser frames pre-checked for deletion.
        </p>
      </div>

      <button
        v-if="groups.length"
        class="btn-danger text-xs sm:text-sm py-2 px-4 shadow-sm"
        @click="cullAll"
      >
        ✂️ Cull All (Keep Best in Each)
      </button>
    </div>

    <div v-if="loading" class="space-y-4">
      <div v-for="i in 3" :key="i" class="card p-4 space-y-3">
        <Skeleton width="8rem" height="0.8rem" />
        <div class="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-5 gap-3">
          <div v-for="j in 4" :key="j" class="skeleton aspect-square rounded-xl" />
        </div>
      </div>
    </div>

    <div v-else-if="groups.length" class="space-y-5">
      <div v-for="group in groups" :key="group.burst_id" class="card p-4 sm:p-5 space-y-3 bg-ink-900/80 border-white/5 shadow-md">
        <div class="flex items-center justify-between border-b border-white/5 pb-2.5">
          <span class="text-xs font-bold text-gray-300 uppercase tracking-wider flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-brand-400" />
            Burst ({{ group.photos.length }} shots)
          </span>
          <button
            class="text-xs text-red-400 hover:text-red-300 font-medium hover:underline flex items-center gap-1"
            @click="cullGroup(group)"
          >
            <span>🗑</span> Cull Checked ({{ checkedFor(group).size }})
          </button>
        </div>

        <!-- Burst Photos Grid -->
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          <div
            v-for="p in group.photos"
            :key="p.id"
            class="group relative flex flex-col gap-1.5"
          >
            <div
              class="aspect-square bg-ink-850 rounded-xl overflow-hidden cursor-pointer transition-all duration-200 border"
              :class="p.id === group.keep_id
                ? 'border-emerald-500/80 ring-2 ring-emerald-500/30'
                : (checkedFor(group).has(p.id) ? 'border-red-500/60 opacity-60' : 'border-white/10 hover:border-white/25')"
              @click="toggle(group, p.id)"
            >
              <img
                v-if="p.thumbnail_url"
                :src="p.thumbnail_url"
                class="w-full h-full object-cover transition-transform duration-200 group-hover:scale-105"
              />
              <div v-else class="w-full h-full flex items-center justify-center text-2xl text-gray-600">🖼️</div>

              <!-- Badges Overlay -->
              <div class="absolute top-2 left-2 flex gap-1">
                <span v-if="p.id === group.keep_id" class="badge bg-emerald-500/90 text-white font-bold text-[10px]">
                  ★ BEST
                </span>
                <span v-else-if="checkedFor(group).has(p.id)" class="badge bg-red-500/90 text-white font-bold text-[10px]">
                  TRASH
                </span>
              </div>
            </div>

            <!-- Card Footer Status -->
            <div class="flex items-center justify-between text-[11px] px-0.5">
              <span v-if="p.quality_score != null" class="font-mono text-gray-400">
                ⭐ {{ Math.round(p.quality_score * 100) }}%
              </span>
              <button
                class="text-[11px] font-semibold transition-colors"
                :class="checkedFor(group).has(p.id) ? 'text-red-400 hover:text-red-300' : 'text-emerald-400 hover:text-emerald-300'"
                @click="toggle(group, p.id)"
              >
                {{ checkedFor(group).has(p.id) ? 'Delete' : 'Keep' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <EmptyState
      v-else
      icon="📸"
      title="No burst sequences detected"
      subtitle="Burst runs taken in rapid succession will be clustered here when you run a library analysis."
    >
      <template #action>
        <router-link to="/cleanup" class="btn-primary text-sm">✨ Run Library Analysis</router-link>
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
  if (id === group.keep_id) return
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
    title: `Cull ${allIds.length} burst photos?`,
    message: 'The highest-quality shot in each burst is kept. Checked frames will move to Trash.',
    confirmText: 'Cull Bursts',
    danger: true,
  })
  if (!ok) return
  await photosApi.bulkDelete(allIds)
  success(`Culled ${allIds.length} photos`)
  await load()
}
</script>
