import { ref, computed } from 'vue'

export function useSelection() {
  const _selected = ref(new Set())
  const selecting = ref(false)

  const selected = computed(() => _selected.value)
  const count = computed(() => _selected.value.size)
  const ids = computed(() => [..._selected.value])

  function toggle(id) {
    const next = new Set(_selected.value)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    _selected.value = next
    selecting.value = next.size > 0
  }

  function selectAll(idList) {
    _selected.value = new Set(idList)
    selecting.value = _selected.value.size > 0
  }

  function clear() {
    _selected.value = new Set()
    selecting.value = false
  }

  function isSelected(id) {
    return _selected.value.has(id)
  }

  return { selected, selecting, count, ids, toggle, selectAll, clear, isSelected }
}
