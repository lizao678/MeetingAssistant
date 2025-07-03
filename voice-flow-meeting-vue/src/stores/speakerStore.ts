import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { speakerService } from '@/services'
import type { FrequentSpeaker } from '@/services'
import { ElMessage } from 'element-plus'

export interface Speaker {
  id: number | string
  name: string
  color: string
  number?: string
  segmentCount?: number
  useCount?: number
  createTime?: string
  lastUsedTime?: string
}

export interface SpeakerSettingData {
  speakerName: string
  settingRange: 'single' | 'global'
  targetSpeaker?: Speaker
}

export const useSpeakerStore = defineStore('speaker', () => {
  // 常用发言人列表
  const frequentSpeakers = ref<Speaker[]>([])
  const loading = ref(false)

  // 默认发言人颜色列表
  const defaultColors = [
    '#ff6b6b', '#4ecdc4', '#45b7d1', '#f9ca24', 
    '#26de81', '#fd79a8', '#fdcb6e', '#6c5ce7',
    '#a29bfe', '#74b9ff', '#00b894', '#e17055'
  ]

  // 计算属性：按使用频率排序的常用发言人
  const sortedFrequentSpeakers = computed(() => {
    return frequentSpeakers.value
      .slice()
      .sort((a, b) => (b.useCount || 0) - (a.useCount || 0))
  })

  // 计算属性：获取下一个可用颜色
  const getNextColor = computed(() => {
    const usedColors = frequentSpeakers.value.map(s => s.color)
    return defaultColors.find(color => !usedColors.includes(color)) || defaultColors[0]
  })

  // 数据转换函数
  const convertFrequentSpeaker = (speaker: FrequentSpeaker): Speaker => {
    return {
      id: speaker.id,
      name: speaker.name,
      color: speaker.color,
      useCount: speaker.useCount,
      createTime: speaker.createdAt,
      lastUsedTime: speaker.lastUsedAt
    }
  }

  // 操作方法

  /**
   * 加载常用发言人列表
   */
  const loadFrequentSpeakers = async () => {
    if (loading.value) return
    
    try {
      loading.value = true
      const speakers = await speakerService.getFrequentSpeakers()
      frequentSpeakers.value = speakers.map(convertFrequentSpeaker)
    } catch (error) {
      console.error('加载常用发言人失败:', error)
      ElMessage.error('加载常用发言人失败')
    } finally {
      loading.value = false
    }
  }
  
  /**
   * 添加常用发言人
   */
  const addFrequentSpeaker = async (speaker: Omit<Speaker, 'id' | 'useCount' | 'createTime'>) => {
    try {
      const newSpeaker = await speakerService.addFrequentSpeaker({
        name: speaker.name,
        color: speaker.color || getNextColor.value
      })
      
      const convertedSpeaker = convertFrequentSpeaker(newSpeaker)
      frequentSpeakers.value.push(convertedSpeaker)
      ElMessage.success('添加常用发言人成功')
      
      return convertedSpeaker
    } catch (error) {
      console.error('添加常用发言人失败:', error)
      ElMessage.error('添加常用发言人失败')
      throw error
    }
  }

  /**
   * 删除常用发言人
   */
  const removeFrequentSpeaker = async (speakerId: number | string) => {
    try {
      await speakerService.deleteFrequentSpeaker(Number(speakerId))
      
      const index = frequentSpeakers.value.findIndex(s => s.id == speakerId)
      if (index !== -1) {
        frequentSpeakers.value.splice(index, 1)
      }
      
      ElMessage.success('删除常用发言人成功')
      return true
    } catch (error) {
      console.error('删除常用发言人失败:', error)
      ElMessage.error('删除常用发言人失败')
      return false
    }
  }

  /**
   * 更新常用发言人信息
   */
  const updateFrequentSpeaker = async (speakerId: number | string, updates: Partial<Speaker>) => {
    try {
      await speakerService.updateFrequentSpeaker(Number(speakerId), {
        name: updates.name,
        color: updates.color
      })
      
      const index = frequentSpeakers.value.findIndex(s => s.id == speakerId)
      if (index !== -1) {
        Object.assign(frequentSpeakers.value[index], updates)
      }
      
      ElMessage.success('更新常用发言人成功')
      return true
    } catch (error) {
      console.error('更新常用发言人失败:', error)
      ElMessage.error('更新常用发言人失败')
      return false
    }
  }

  /**
   * 增加发言人使用次数（这个由后端在设置发言人时自动处理）
   */
  const incrementSpeakerUsage = (speakerId: number | string) => {
    const speaker = frequentSpeakers.value.find(s => s.id == speakerId)
    if (speaker) {
      speaker.useCount = (speaker.useCount || 0) + 1
      speaker.lastUsedTime = new Date().toISOString()
    }
  }

  /**
   * 更新录音中的发言人信息
   */
  const updateSpeakerInRecording = async (
    recordingId: string, 
    speakerId: string, 
    newName: string,
    settingType: 'single' | 'global' = 'single',
    frequentSpeakerId?: number
  ) => {
    try {
      await speakerService.updateSpeakerInRecording(recordingId, speakerId, {
        new_name: newName,
        setting_type: settingType,
        frequent_speaker_id: frequentSpeakerId
      })
      
      // 如果使用了常用发言人，增加使用次数
      if (frequentSpeakerId) {
        incrementSpeakerUsage(frequentSpeakerId)
      }
      
      ElMessage.success('更新发言人信息成功')
      return true
    } catch (error) {
      console.error('更新发言人信息失败:', error)
      ElMessage.error('更新发言人信息失败')
      return false
    }
  }

  /**
   * 根据名称查找常用发言人
   */
  const findSpeakerByName = (name: string) => {
    return frequentSpeakers.value.find(s => s.name === name)
  }

  /**
   * 获取发言人建议（基于历史使用）
   */
  const getSpeakerSuggestions = (inputName: string, limit: number = 5) => {
    if (!inputName.trim()) {
      return sortedFrequentSpeakers.value.slice(0, limit)
    }
    
    const normalizedInput = inputName.toLowerCase()
    return frequentSpeakers.value
      .filter(s => s.name.toLowerCase().includes(normalizedInput))
      .sort((a, b) => (b.useCount || 0) - (a.useCount || 0))
      .slice(0, limit)
  }

  /**
   * 清理未使用的发言人（注意：这只是本地清理，服务器数据不会被删除）
   */
  const cleanupUnusedSpeakers = (daysThreshold: number = 30) => {
    const threshold = new Date()
    threshold.setDate(threshold.getDate() - daysThreshold)
    
    const before = frequentSpeakers.value.length
    const speakersToRemove: Speaker[] = []
    
    frequentSpeakers.value.forEach(speaker => {
      if (!speaker.useCount || speaker.useCount === 0) {
        speakersToRemove.push(speaker)
      } else if (speaker.lastUsedTime && new Date(speaker.lastUsedTime) <= threshold) {
        speakersToRemove.push(speaker)
      }
    })
    
    // 通过API删除（可选）或者只是从本地列表中移除
    speakersToRemove.forEach(speaker => {
      const index = frequentSpeakers.value.findIndex(s => s.id === speaker.id)
      if (index !== -1) {
        frequentSpeakers.value.splice(index, 1)
      }
    })
    
    return speakersToRemove.length
  }

  /**
   * 导出常用发言人数据
   */
  const exportFrequentSpeakers = () => {
    const data = {
      version: '1.0',
      exportTime: new Date().toISOString(),
      speakers: frequentSpeakers.value
    }
    
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `voice-flow-speakers-${new Date().toISOString().split('T')[0]}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  /**
   * 导入常用发言人数据（暂时保留，但需要通过API同步）
   */
  const importFrequentSpeakers = async (file: File): Promise<boolean> => {
    return new Promise((resolve) => {
      const reader = new FileReader()
      reader.onload = async (e) => {
        try {
          const content = e.target?.result as string
          const data = JSON.parse(content)
          
          if (data.speakers && Array.isArray(data.speakers)) {
            // 合并导入的发言人，避免重复
            const existingNames = new Set(frequentSpeakers.value.map(s => s.name))
            const newSpeakers = data.speakers.filter((s: Speaker) => !existingNames.has(s.name))
            
            // 通过API添加新的发言人
            for (const speaker of newSpeakers) {
              try {
                await addFrequentSpeaker({
                  name: speaker.name,
                  color: speaker.color
                })
              } catch (error) {
                console.error(`导入发言人 ${speaker.name} 失败:`, error)
              }
            }
            
            resolve(true)
          } else {
            throw new Error('无效的文件格式')
          }
        } catch (error) {
          console.error('导入常用发言人失败:', error)
          resolve(false)
        }
      }
      reader.readAsText(file)
    })
  }

  return {
    // 状态
    frequentSpeakers,
    loading,
    defaultColors,
    
    // 计算属性
    sortedFrequentSpeakers,
    getNextColor,
    
    // 操作方法
    loadFrequentSpeakers,
    addFrequentSpeaker,
    removeFrequentSpeaker,
    updateFrequentSpeaker,
    updateSpeakerInRecording,
    incrementSpeakerUsage,
    findSpeakerByName,
    getSpeakerSuggestions,
    cleanupUnusedSpeakers,
    
    // 导入导出方法
    exportFrequentSpeakers,
    importFrequentSpeakers
  }
}) 