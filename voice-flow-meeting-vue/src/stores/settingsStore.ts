import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { AudioSettings } from '@/types/audio'

export interface UserSettings {
  // 语音识别设置
  defaultLanguage: string
  enableSpeakerRecognition: boolean
  enableSmartBreaks: boolean
  enablePunctuation: boolean
  
  // 显示设置
  theme: 'light' | 'dark' | 'auto'
  fontSize: 'small' | 'medium' | 'large'
  messageDisplayMode: 'bubble' | 'list'
  showTimestamps: boolean
  
  // 音频设置
  audioDevice: string
  enableNoiseReduction: boolean
  enableEchoCancellation: boolean
  audioQuality: 'low' | 'medium' | 'high'
  
  // 存储设置
  autoSave: boolean
  saveLocation: 'local' | 'cloud'
  maxLocalStorage: number // MB
  
  // 通知设置
  enableNotifications: boolean
  notificationSound: boolean
  errorNotifications: boolean
  
  // AI功能设置
  autoGenerateSummary: boolean
  autoExtractKeywords: boolean
  enableSentimentAnalysis: boolean
  summaryLanguage: string
  
  // 隐私设置
  enableLocalProcessing: boolean
  shareAnalyticsData: boolean
  retainAudioData: boolean
}

export const useSettingsStore = defineStore('settings', () => {
  // 默认设置
  const defaultSettings: UserSettings = {
    // 语音识别设置
    defaultLanguage: 'auto',
    enableSpeakerRecognition: true,
    enableSmartBreaks: true,
    enablePunctuation: true,
    
    // 显示设置
    theme: 'auto',
    fontSize: 'medium',
    messageDisplayMode: 'bubble',
    showTimestamps: true,
    
    // 音频设置
    audioDevice: '',
    enableNoiseReduction: true,
    enableEchoCancellation: true,
    audioQuality: 'medium',
    
    // 存储设置
    autoSave: true,
    saveLocation: 'local',
    maxLocalStorage: 500,
    
    // 通知设置
    enableNotifications: true,
    notificationSound: false,
    errorNotifications: true,
    
    // AI功能设置
    autoGenerateSummary: false,
    autoExtractKeywords: true,
    enableSentimentAnalysis: false,
    summaryLanguage: 'zh-CN',
    
    // 隐私设置
    enableLocalProcessing: false,
    shareAnalyticsData: false,
    retainAudioData: true
  }
  
  // 当前设置
  const settings = ref<UserSettings>({ ...defaultSettings })
  
  // 设置是否已修改（未保存）
  const hasUnsavedChanges = ref(false)
  
  // 支持的语言列表
  const supportedLanguages = ref([
    { code: 'auto', name: '自动检测' },
    { code: 'zh-CN', name: '中文(普通话)' },
    { code: 'en-US', name: 'English (US)' },
    { code: 'en-GB', name: 'English (UK)' },
    { code: 'ja-JP', name: '日本語' },
    { code: 'ko-KR', name: '한국어' },
    { code: 'es-ES', name: 'Español' },
    { code: 'fr-FR', name: 'Français' },
  ])
  
  // 音频设置
  const speechSettings = ref<AudioSettings>({
    defaultLanguage: 'zh',
    enableVAD: true,
    vadThreshold: 0.5,
    enableNoiseSuppression: true,
    enableEchoCancellation: true,
    sampleRate: 16000,
    enableRealTimeTranscription: true,
    maxSpeechLength: 60,
    enableAudioEnhancement: true,
    enhancementLevel: 'medium',
    enableAutoGain: true
  })
  
  // 操作方法
  const updateSetting = <K extends keyof UserSettings>(
    key: K, 
    value: UserSettings[K]
  ) => {
    settings.value[key] = value
    hasUnsavedChanges.value = true
  }
  
  const updateSettings = (newSettings: Partial<UserSettings>) => {
    Object.assign(settings.value, newSettings)
    hasUnsavedChanges.value = true
  }
  
  const resetToDefaults = () => {
    settings.value = { ...defaultSettings }
    hasUnsavedChanges.value = true
  }
  
  const resetCategory = (category: 'speech' | 'display' | 'audio' | 'storage' | 'notification' | 'ai' | 'privacy') => {
    switch (category) {
      case 'speech':
        settings.value.defaultLanguage = defaultSettings.defaultLanguage
        settings.value.enableSpeakerRecognition = defaultSettings.enableSpeakerRecognition
        settings.value.enableSmartBreaks = defaultSettings.enableSmartBreaks
        settings.value.enablePunctuation = defaultSettings.enablePunctuation
        break
      case 'display':
        settings.value.theme = defaultSettings.theme
        settings.value.fontSize = defaultSettings.fontSize
        settings.value.messageDisplayMode = defaultSettings.messageDisplayMode
        settings.value.showTimestamps = defaultSettings.showTimestamps
        break
      case 'audio':
        settings.value.audioDevice = defaultSettings.audioDevice
        settings.value.enableNoiseReduction = defaultSettings.enableNoiseReduction
        settings.value.enableEchoCancellation = defaultSettings.enableEchoCancellation
        settings.value.audioQuality = defaultSettings.audioQuality
        break
      case 'storage':
        settings.value.autoSave = defaultSettings.autoSave
        settings.value.saveLocation = defaultSettings.saveLocation
        settings.value.maxLocalStorage = defaultSettings.maxLocalStorage
        break
      case 'notification':
        settings.value.enableNotifications = defaultSettings.enableNotifications
        settings.value.notificationSound = defaultSettings.notificationSound
        settings.value.errorNotifications = defaultSettings.errorNotifications
        break
      case 'ai':
        settings.value.autoGenerateSummary = defaultSettings.autoGenerateSummary
        settings.value.autoExtractKeywords = defaultSettings.autoExtractKeywords
        settings.value.enableSentimentAnalysis = defaultSettings.enableSentimentAnalysis
        settings.value.summaryLanguage = defaultSettings.summaryLanguage
        break
      case 'privacy':
        settings.value.enableLocalProcessing = defaultSettings.enableLocalProcessing
        settings.value.shareAnalyticsData = defaultSettings.shareAnalyticsData
        settings.value.retainAudioData = defaultSettings.retainAudioData
        break
    }
    hasUnsavedChanges.value = true
  }
  
  // 保存设置到本地存储
  const saveSettings = () => {
    try {
      localStorage.setItem('voice-flow-settings', JSON.stringify(settings.value))
      hasUnsavedChanges.value = false
      return true
    } catch (error) {
      console.error('保存设置失败:', error)
      return false
    }
  }
  
  // 从本地存储加载设置
  const loadSettings = () => {
    try {
      const saved = localStorage.getItem('voice-flow-settings')
      if (saved) {
        const parsedSettings = JSON.parse(saved)
        // 合并设置，确保新增的设置项有默认值
        settings.value = { ...defaultSettings, ...parsedSettings }
      }
      hasUnsavedChanges.value = false
      return true
    } catch (error) {
      console.error('加载设置失败:', error)
      return false
    }
  }
  
  // 导出设置
  const exportSettings = () => {
    const dataStr = JSON.stringify(settings.value, null, 2)
    const dataBlob = new Blob([dataStr], { type: 'application/json' })
    const url = URL.createObjectURL(dataBlob)
    
    const link = document.createElement('a')
    link.href = url
    link.download = `voice-flow-settings-${Date.now()}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }
  
  // 导入设置
  const importSettings = (file: File): Promise<boolean> => {
    return new Promise((resolve) => {
      const reader = new FileReader()
      reader.onload = (e) => {
        try {
          const importedSettings = JSON.parse(e.target?.result as string)
          // 验证导入的设置格式
          if (typeof importedSettings === 'object' && importedSettings !== null) {
            settings.value = { ...defaultSettings, ...importedSettings }
            hasUnsavedChanges.value = true
            resolve(true)
          } else {
            resolve(false)
          }
        } catch (error) {
          console.error('导入设置失败:', error)
          resolve(false)
        }
      }
      reader.readAsText(file)
    })
  }
  
  // 获取当前主题
  const getCurrentTheme = () => {
    if (settings.value.theme === 'auto') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    }
    return settings.value.theme
  }
  
  // 获取存储使用情况
  const getStorageUsage = () => {
    try {
      let totalSize = 0
      for (const key in localStorage) {
        if (localStorage.hasOwnProperty(key)) {
          totalSize += localStorage[key].length
        }
      }
      // 转换为MB
      const usedMB = totalSize / (1024 * 1024)
      const maxMB = settings.value.maxLocalStorage
      
      return {
        used: Math.round(usedMB * 100) / 100,
        max: maxMB,
        percentage: Math.round((usedMB / maxMB) * 100)
      }
    } catch (error) {
      console.error('获取存储使用情况失败:', error)
      return { used: 0, max: settings.value.maxLocalStorage, percentage: 0 }
    }
  }
  
  // 清理本地存储
  const clearLocalStorage = (types: ('recordings' | 'cache' | 'logs')[] = ['cache', 'logs']) => {
    try {
      types.forEach(type => {
        switch (type) {
          case 'recordings':
            // 清理录音相关数据
            for (const key in localStorage) {
              if (key.startsWith('recording-') || key.startsWith('audio-')) {
                localStorage.removeItem(key)
              }
            }
            break
          case 'cache':
            // 清理缓存数据
            for (const key in localStorage) {
              if (key.startsWith('cache-') || key.startsWith('temp-')) {
                localStorage.removeItem(key)
              }
            }
            break
          case 'logs':
            // 清理日志数据
            for (const key in localStorage) {
              if (key.startsWith('log-') || key.startsWith('error-')) {
                localStorage.removeItem(key)
              }
            }
            break
        }
      })
      return true
    } catch (error) {
      console.error('清理本地存储失败:', error)
      return false
    }
  }
  
  return {
    // 状态
    settings,
    hasUnsavedChanges,
    supportedLanguages,
    defaultSettings,
    speechSettings,
    
    // 方法
    updateSetting,
    updateSettings,
    resetToDefaults,
    resetCategory,
    saveSettings,
    loadSettings,
    exportSettings,
    importSettings,
    getCurrentTheme,
    getStorageUsage,
    clearLocalStorage
  }
}) 