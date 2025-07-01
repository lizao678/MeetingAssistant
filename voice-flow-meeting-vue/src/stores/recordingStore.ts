import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Recording, RecordingFilter } from '../services/recordingService'

export const useRecordingStore = defineStore('recording', () => {
  // 状态
  const recordings = ref<Recording[]>([])
  const currentRecording = ref<Recording | null>(null)
  const loading = ref(false)
  const filter = ref<RecordingFilter>({})
  
  // 计算属性
  const filteredRecordings = computed(() => {
    let result = recordings.value
    
    if (filter.value.search) {
      const searchTerm = filter.value.search.toLowerCase()
      result = result.filter(r => 
        r.title.toLowerCase().includes(searchTerm) ||
        r.description.toLowerCase().includes(searchTerm) ||
        r.preview.toLowerCase().includes(searchTerm)
      )
    }
    
    if (filter.value.status) {
      result = result.filter(r => r.status === filter.value.status)
    }
    
    if (filter.value.tags && filter.value.tags.length > 0) {
      result = result.filter(r => 
        filter.value.tags!.some(tag => r.tags.includes(tag))
      )
    }
    
    return result
  })
  
  const completedRecordings = computed(() => 
    recordings.value.filter(r => r.status === 'completed')
  )
  
  const processingRecordings = computed(() => 
    recordings.value.filter(r => r.status === 'processing')
  )
  
  const totalDuration = computed(() => {
    return recordings.value.reduce((total, recording) => {
      const [minutes, seconds] = recording.duration.split(':').map(Number)
      return total + minutes * 60 + seconds
    }, 0)
  })
  
  // 操作
  const setRecordings = (newRecordings: Recording[]) => {
    recordings.value = newRecordings
  }
  
  const addRecording = (recording: Recording) => {
    recordings.value.unshift(recording)
  }
  
  const updateRecording = (id: string, updates: Partial<Recording>) => {
    const index = recordings.value.findIndex(r => r.id === id)
    if (index > -1) {
      recordings.value[index] = { ...recordings.value[index], ...updates }
    }
  }
  
  const removeRecording = (id: string) => {
    const index = recordings.value.findIndex(r => r.id === id)
    if (index > -1) {
      recordings.value.splice(index, 1)
    }
  }
  
  const setCurrentRecording = (recording: Recording | null) => {
    currentRecording.value = recording
  }
  
  const setFilter = (newFilter: RecordingFilter) => {
    filter.value = { ...filter.value, ...newFilter }
  }
  
  const clearFilter = () => {
    filter.value = {}
  }
  
  const setLoading = (isLoading: boolean) => {
    loading.value = isLoading
  }
  
  // 批量操作
  const removeMultipleRecordings = (ids: string[]) => {
    recordings.value = recordings.value.filter(r => !ids.includes(r.id))
  }
  
  const updateMultipleRecordings = (ids: string[], updates: Partial<Recording>) => {
    recordings.value = recordings.value.map(r => 
      ids.includes(r.id) ? { ...r, ...updates } : r
    )
  }
  
  return {
    // 状态
    recordings,
    currentRecording,
    loading,
    filter,
    // 计算属性
    filteredRecordings,
    completedRecordings,
    processingRecordings,
    totalDuration,
    // 操作
    setRecordings,
    addRecording,
    updateRecording,
    removeRecording,
    setCurrentRecording,
    setFilter,
    clearFilter,
    setLoading,
    removeMultipleRecordings,
    updateMultipleRecordings
  }
}) 