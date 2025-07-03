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

interface SpeechSettings {
  defaultLanguage: string
  sampleRate: number
  maxSpeechLength: number
  enableVAD: boolean
  vadThreshold: number
  enableNoiseSuppression: boolean
  enableEchoCancellation: boolean
  enableRealTimeTranscription: boolean
}

interface SettingsState {
  speechSettings: SpeechSettings
}

export const useSettingsStore = defineStore('settings', {
  state: (): SettingsState => ({
    speechSettings: {
      defaultLanguage: 'zh',
      sampleRate: 16000,
      maxSpeechLength: 300,
      enableVAD: true,
      vadThreshold: 0.5,
      enableNoiseSuppression: true,
      enableEchoCancellation: true,
      enableRealTimeTranscription: true
    }
  }),

  actions: {
    loadSettings() {
      const savedSettings = localStorage.getItem('voice-flow-settings')
      if (savedSettings) {
        try {
          const parsed = JSON.parse(savedSettings)
          this.speechSettings = {
            ...this.speechSettings,
            ...parsed.speechSettings
          }
        } catch (error) {
          console.error('Failed to load settings:', error)
        }
      }
    },

    saveSettings() {
      try {
        localStorage.setItem('voice-flow-settings', JSON.stringify({
          speechSettings: this.speechSettings
        }))
      } catch (error) {
        console.error('Failed to save settings:', error)
      }
    },

    resetSettings() {
      this.speechSettings = {
        defaultLanguage: 'zh',
        sampleRate: 16000,
        maxSpeechLength: 300,
        enableVAD: true,
        vadThreshold: 0.5,
        enableNoiseSuppression: true,
        enableEchoCancellation: true,
        enableRealTimeTranscription: true
      }
      this.saveSettings()
    }
  }
}) 