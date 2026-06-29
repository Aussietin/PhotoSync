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
          <Spinner v-if="scanning" :size="16" />
          {{ scanning ? 'Scanning…' : '🔍 Re-scan' }}
        </button>
        <button
          v-if="groups.length"
          class="btn-danger text-sm"
          @click="deleteAllSuggested"
        >Delete all suggested</button>
      </div>
    </div>

    <div v-if="loading" class="space-y-6">
      <div v-for="i in 3" :key="i" class="card p-4 space-y-3">
        <Skeleton width="12rem" height="0.7rem" />
        <div class="grid grid-cols-4 gap-2">
          <div v-for="j in 4" :key="j" class="skeleton aspect-square rounded-xl" />
        </div>
      </div>
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

    <EmptyState
      v-else
      icon="✅"
      title="No duplicates found"
      subtitle="Your library is squeaky clean. Re-scan any time after adding new photos."
    >
      <template #action>
        <button class="btn-soft text-sm" :disabled="scanning" @click="rescan">🔍 Re-scan</button>
      </template>
    </EmptyState>
  </div>
</template>

<script setup>
import { ref, computed, reactive, onMounted } from 'vue'
import { photosApi } from '../api/photos'
import { useJob } from '../composables/useJob'
import Skeleton from '../components/ui/Skeleton.vue'
import Spinner from '../components/ui/Spinner.vue'
import EmptyState from '../components/ui/EmptyState.vue'
import { useToast } from '../composables/useToast'
import { useConfirm } from '../composables/useConfirm'

const { success } = useToast()
const { confirm } = useConfirm()
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
  success(`Removed ${ids.length} duplicate${ids.length > 1 ? 's' : ''}`)
}

async function deleteAllSuggested() {
  const allIds = groups.value.flatMap((g) => [...(checked[g.original.id] ?? [])])
  if (!allIds.length) return
  const ok = await confirm({
    title: `Delete ${allIds.length} suggested duplicate${allIds.length > 1 ? 's' : ''}?`,
    message: 'The best copy in each group is kept. Deleted photos go to Trash.',
    confirmText: 'Delete duplicates',
    danger: true,
  })
  if (!ok) return
  await photosApi.bulkDelete(allIds)
  success(`Removed ${allIds.length} duplicates`)
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
