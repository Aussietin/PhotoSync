<template>
  <div>
    <div class="flex items-center justify-between mb-5">
      <div>
        <h1 class="text-xl font-bold">
          Duplicates
          <span class="text-gray-500 font-normal text-base">({{ summary }})</span>
        </h1>
        <p class="text-xs text-gray-500 mt-0.5">Auto-selected duplicates are pre-checked — review and delete</p>
      </div>
      <div class="flex gap-2">
        <button class="btn-ghost text-sm" :disabled="scanning" @click="rescan">
          {{ scanning ? 'Scanning…' : '🔍 Re-scan' }}
        </button>
        <button
          v-if="groups.length"
          class="btn-ghost text-sm text-red-400 hover:text-red-300"
          @click="deleteAllSuggested"
        >Delete all suggested</button>
      </div>
    </div>

    <div v-if="loading" class="flex justify-center py-20">
      <span class="text-gray-500 animate-pulse">Loading…</span>
    </div>

    <div v-else-if="groups.length" class="space-y-6">
      <div v-for="group in groups" :key="group.original.id" class="card p-4">
        <!-- Group header -->
        <div class="flex items-center justify-between mb-3">
          <span class="text-xs text-gray-500 font-medium uppercase tracking-wider">
            1 original + {{ group.duplicates.length }} duplicate{{ group.duplicates.length !== 1 ? 's' : '' }}
          </span>
          <button
            class="text-xs text-red-400 hover:text-red-300"
            @click="deleteChecked(group)"
          >Delete checked</button>
        </div>

        <!-- Side-by-side grid: original first, then duplicates -->
        <div class="grid gap-2" :style="gridCols(group.duplicates.length + 1)">
          <!-- Original -->
          <div class="relative">
            <div class="aspect-square bg-gray-800 rounded-xl overflow-hidden">
              <img
                v-if="group.original.thumbnail_url"
                :src="group.original.thumbnail_url"
                class="w-full h-full object-cover"
              />
            </div>
            <div class="mt-1 text-center">
              <span class="text-xs bg-green-500/20 text-green-400 px-2 py-0.5 rounded-full">Original</span>
            </div>
            <div class="text-xs text-gray-500 text-center mt-0.5 truncate">
              {{ quality(group.original) }}
            </div>
          </div>

          <!-- Duplicates -->
          <div v-for="dup in group.duplicates" :key="dup.id" class="relative">
            <div
              class="aspect-square bg-gray-800 rounded-xl overflow-hidden cursor-pointer transition-all"
              :class="isChecked(group, dup.id) ? 'ring-2 ring-red-500' : 'ring-1 ring-gray-700 hover:ring-gray-500'"
              @click="toggleCheck(group, dup.id)"
            >
              <img
                v-if="dup.thumbnail_url"
                :src="dup.thumbnail_url"
                class="w-full h-full object-cover"
                :class="isChecked(group, dup.id) && 'opacity-60'"
              />
              <!-- Delete overlay -->
              <div v-if="isChecked(group, dup.id)" class="absolute inset-0 flex items-center justify-center">
                <span class="text-3xl text-red-500">✕</span>
              </div>
            </div>
            <div class="mt-1 text-center">
              <span
                class="text-xs px-2 py-0.5 rounded-full cursor-pointer select-none"
                :class="isChecked(group, dup.id) ? 'bg-red-500/20 text-red-400' : 'bg-gray-700 text-gray-400'"
                @click="toggleCheck(group, dup.id)"
              >{{ isChecked(group, dup.id) ? 'Delete' : 'Keep' }}</span>
            </div>
            <div class="text-xs text-gray-500 text-center mt-0.5 truncate">
              {{ quality(dup) }}
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="flex flex-col items-center py-20 text-gray-600">
      <span class="text-5xl mb-4">✅</span>
      <p>No duplicates found — your library is clean!</p>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { photosApi } from '../api/photos'
import { useJob } from '../composables/useJob'

const { track } = useJob()

const groups = ref([])
const loading = ref(false)
const scanning = ref(false)
// Map of group original id → Set of checked (to-delete) photo ids
const checked = reactive({})

const summary = computed(() => {
  const g = groups.value.length
  const d = groups.value.reduce((n, g) => n + g.duplicates.length, 0)
  return g ? `${g} group${g !== 1 ? 's' : ''}, ${d} duplicate${d !== 1 ? 's' : ''}` : '0'
})

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await photosApi.duplicateGroups()
    groups.value = data.groups
    // Pre-check suggested deletes
    for (const group of data.groups) {
      checked[group.original.id] = new Set(group.suggested_delete_ids)
    }
  } finally {
    loading.value = false
  }
})

function isChecked(group, id) {
  return checked[group.original.id]?.has(id) ?? false
}

function toggleCheck(group, id) {
  const s = checked[group.original.id] ?? new Set()
  const next = new Set(s)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  checked[group.original.id] = next
}

async function deleteChecked(group) {
  const ids = [...(checked[group.original.id] ?? [])]
  if (!ids.length) return
  await photosApi.bulkDelete(ids)
  groups.value = groups.value
    .map((g) =>
      g.original.id === group.original.id
        ? { ...g, duplicates: g.duplicates.filter((d) => !ids.includes(d.id)) }
        : g
    )
    .filter((g) => g.duplicates.length)
  delete checked[group.original.id]
}

async function deleteAllSuggested() {
  const allIds = groups.value.flatMap((g) => [...(checked[g.original.id] ?? [])])
  if (!allIds.length) return
  if (!confirm(`Delete ${allIds.length} suggested duplicates?`)) return
  await photosApi.bulkDelete(allIds)
  await reload()
}

async function reload() {
  loading.value = true
  try {
    const { data } = await photosApi.duplicateGroups()
    groups.value = data.groups
    for (const group of data.groups) {
      checked[group.original.id] = new Set(group.suggested_delete_ids)
    }
  } finally {
    loading.value = false
  }
}

async function rescan() {
  scanning.value = true
  try {
    const { data } = await photosApi.rescanDuplicates()
    // Now a background job — wait for it before reloading the groups.
    await track(data.job_id, {
      onDone: async () => { await reload(); scanning.value = false },
      onError: () => { scanning.value = false },
    })
  } catch (e) {
    scanning.value = false
  }
}

function gridCols(count) {
  const cols = Math.min(count, 6)
  return { gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }
}

function quality(photo) {
  if (photo.quality_score == null) return ''
  return `Quality ${Math.round(photo.quality_score * 100)}%`
}
</script>
