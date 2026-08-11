import { defineStore } from 'pinia'
import { ref } from 'vue'
import { cockpitAPI, type CockpitSummary } from '../api/cockpit'

export const useCockpitStore = defineStore('cockpit', () => {
  const summary = ref<CockpitSummary | null>(null)
  const currentPeriod = ref('30d')
  const loading = ref(false)

  async function fetchSummary(period: string = '30d') {
    loading.value = true
    try {
      currentPeriod.value = period
      summary.value = await cockpitAPI.getSummary(period)
    } finally {
      loading.value = false
    }
  }

  return { summary, currentPeriod, loading, fetchSummary }
})