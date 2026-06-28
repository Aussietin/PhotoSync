import { ref, onBeforeUnmount } from 'vue'
import { jobsApi } from '../api/photos'

/**
 * Poll a background job until it finishes.
 * Usage: const { job, polling, track } = useJob()
 *        await track(jobId, { onDone, onError })
 */
export function useJob() {
  const job = ref(null)
  const polling = ref(false)
  let timer = null

  function stop() {
    polling.value = false
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  async function track(jobId, { interval = 1000, onDone, onError } = {}) {
    stop()
    polling.value = true
    const tick = async () => {
      try {
        const { data } = await jobsApi.get(jobId)
        job.value = data
        if (data.status === 'done') {
          stop()
          onDone?.(data)
        } else if (data.status === 'error') {
          stop()
          onError?.(data)
        } else {
          timer = setTimeout(tick, interval)
        }
      } catch (e) {
        stop()
        onError?.({ error: e.message })
      }
    }
    await tick()
  }

  onBeforeUnmount(stop)
  return { job, polling, track, stop }
}
