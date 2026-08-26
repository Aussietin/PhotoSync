<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-center justify-between gap-3 bg-ink-900/60 p-4 rounded-2xl border border-white/5 backdrop-blur-md">
      <div>
        <h1 class="text-xl font-extrabold tracking-tight text-white flex items-center gap-2">
          <span>Duplicates & Near-Matches</span>
          <span class="text-xs font-mono font-bold px-2 py-0.5 rounded-full bg-brand-500/20 text-brand-300 border border-brand-400/20">
            {{ summary }}
          </span>
        </h1>
        <p class="text-xs text-gray-400 mt-1">
          Near-identical shots grouped by perceptual similarity. The highest quality copy is protected as original.
        </p>
      </div>

      <div class="flex items-center gap-2 flex-wrap">
        <button class="btn-ghost text-xs sm:text-sm py-2 px-3" :disabled="scanning" @click="rescan">
          <Spinner v-if="scanning" :size="16" />
          {{ scanning ? 'Scanning…' : '🔍 Re-scan Duplicates' }}
        </button>
        <button
          v-if="groups.length"
          class="btn-danger text-xs sm:text-sm py-2 px-4 shadow-sm"
          @click="deleteAllSuggested"
        >
          🗑 Delete All Suggested
        </button>
      </div>
    </div>

    <!-- Skeleton Loading -->
    <div v-if="loading" class="space-y-4">
      <div v-for="i in 3" :key="i" class="card p-4 space-y-3">
        <Skeleton width="12rem" height="0.8rem" />
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
          <div v-for="j in 3" :key="j" class="skeleton aspect-square rounded-xl" />
        </div>
      </div>
    </div>

    <!-- Duplicate Groups List -->
    <div v-else-if="groups.length" class="space-y-6">
      <div
        v-for="group in groups"
        :key="group.original.id"
        class="card p-4 sm:p-5 space-y-4 bg-ink-900/80 border-white/5 shadow-md"
      >
        <!-- Group Header -->
        <div class="flex items-center justify-between border-b border-white/5 pb-3">
          <div class="flex items-center gap-2">
            <span class="w-2.5 h-2.5 rounded-full bg-amber-400" />
            <span class="text-xs font-bold text-gray-200 uppercase tracking-wider">
              1 Original + {{ group.duplicates.length }} Duplicate{{ group.duplicates.length !== 1 ? 's' : '' }}
            </span>
          </div>
          <button
            class="text-xs text-red-400 hover:text-red-300 font-medium hover:underline flex items-center gap-1"
            @click="deleteChecked(group)"
          >
            <span>🗑</span> Delete Checked
          </button>
        </div>

        <!-- Comparative Grid -->
        <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
          <!-- Master Original Card -->
          <div class="flex flex-col gap-1.5">
            <div class="aspect-square bg-ink-850 rounded-xl overflow-hidden border-2 border-emerald-500/80 relative shadow-md group">
              <img
                v-if="group.original.thumbnail_url"
                :src="group.original.thumbnail_url"
                class="w-full h-full object-cover transition-transform duration-200 group-hover:scale-105"
              />
              <div v-else class="w-full h-full flex items-center justify-center text-2xl text-gray-600">🖼️</div>

              <!-- Original Pill -->
              <span class="absolute top-2 left-2 badge bg-emerald-500/90 text-white font-bold text-[10px]">
                ★ KEEPER
              </span>
            </div>

            <div class="flex items-center justify-between text-[11px] text-gray-400 px-0.5">
              <span class="font-mono">{{ formatBytes(group.original.file_size) }}</span>
              <span v-if="group.original.quality_score != null" class="font-semibold text-emerald-400">
                ⭐ {{ Math.round(group.original.quality_score * 100) }}%
              </span>
            </div>
          </div>

          <!-- Duplicate Candidates -->
          <div
            v-for="dup in group.duplicates"
            :key="dup.id"
            class="flex flex-col gap-1.5 group"
          >
            <div
              class="aspect-square bg-ink-850 rounded-xl overflow-hidden cursor-pointer transition-all duration-200 border relative"
              :class="isChecked(group, dup.id) ? 'border-red-500/80 ring-2 ring-red-500/30 opacity-70' : 'border-white/10 hover:border-white/30'"
              @click="toggleCheck(group, dup.id)"
            >
              <img
                v-if="dup.thumbnail_url"
                :src="dup.thumbnail_url"
                class="w-full h-full object-cover transition-transform duration-200 group-hover:scale-105"
              />
              <div v-else class="w-full h-full flex items-center justify-center text-2xl text-gray-600">🖼️</div>

              <!-- Delete status badge -->
              <span
                class="absolute top-2 left-2 badge text-[10px]"
                :class="isChecked(group, dup.id) ? 'bg-red-500/90 text-white' : 'bg-ink-800/80 text-gray-300 border border-white/10'"
              >
                {{ isChecked(group, dup.id) ? 'TRASH' : 'KEEP' }}
              </span>
            </div>

            <div class="flex items-center justify-between text-[11px] px-0.5">
              <span class="font-mono text-gray-400">{{ formatBytes(dup.file_size) }}</span>
              <button
                class="text-[11px] font-semibold transition-colors"
                :class="isChecked(group, dup.id) ? 'text-red-400 hover:text-red-300' : 'text-emerald-400 hover:text-emerald-300'"
                @click="toggleCheck(group, dup.id)"
              >
                {{ isChecked(group, dup.id) ? 'Delete' : 'Keep' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <EmptyState
      v-else
      icon="✨"
      title="No duplicates found"
      subtitle="Your photo library has no duplicate clusters. Run a re-scan anytime after adding new files."
    >
      <template #action>
        <button class="btn-primary text-sm" :disabled="scanning" @click="rescan">
          {{ scanning ? 'Scanning…' : '🔍 Re-scan Library' }}
        </button>
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
const checked = reactive({})

const summary = computed(() => {
  const g = groups.value.length
  const d = groups.value.reduce((n, g) => n + g.duplicates.length, 0)
  return g ? `${g} group${g !== 1 ? 's' : ''}, ${d} duplicate${d !== 1 ? 's' : ''}` : '0 duplicates'
})

onMounted(async () => {
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
    title: `Move ${allIds.length} suggested duplicate${allIds.length > 1 ? 's' : ''} to Trash?`,
    message: 'The original keeper in each cluster is retained. Removed files can be restored from Trash.',
    confirmText: 'Move to Trash',
    danger: true,
  })
  if (!ok) return
  await photosApi.bulkDelete(allIds)
  success(`Moved ${allIds.length} duplicates to Trash`)
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
    await track(data.job_id, {
      onDone: async () => {
        await reload()
        scanning.value = false
        success('Duplicate scan completed')
      },
      onError: () => { scanning.value = false },
    })
  } catch (e) {
    scanning.value = false
  }
}

function formatBytes(b) {
  if (!b) return '0 B'
  if (b < 1048576) return `${(b / 1024).toFixed(0)} KB`
  if (b < 1073741824) return `${(b / 1048576).toFixed(1)} MB`
  return `${(b / 1073741824).toFixed(2)} GB`
}
</script>
