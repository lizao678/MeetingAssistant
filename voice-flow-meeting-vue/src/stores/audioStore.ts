import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface AudioMessage {
  id: string
  speaker: string
  text: string
  timestamp: string
  isFinal: boolean
}

export interface WebSocketConfig {
  language: string
  enableSpeakerRecognition: boolean
  enableSmartBreaks: boolean
}

export const useAudioStore = defineStore('audio', () => {
  // WebSocket连接状态
  const websocket = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const isConnecting = ref(false)
  const connectionError = ref<string | null>(null)
  
  // 音频录制状态
  const isRecording = ref(false)
  const isPaused = ref(false)
  const recordingDuration = ref(0)
  
  // 实时转写消息
  const messages = ref<AudioMessage[]>([])
  const currentMessage = ref<AudioMessage | null>(null)
  
  // 音频配置
  const config = ref<WebSocketConfig>({
    language: 'auto',
    enableSpeakerRecognition: true,
    enableSmartBreaks: true
  })
  
  // 音频设备
  const mediaStream = ref<MediaStream | null>(null)
  const audioDevices = ref<MediaDeviceInfo[]>([])
  const selectedDevice = ref<string>('')
  
  // 音频可视化
  const audioLevel = ref(0)
  const frequencyData = ref<Uint8Array | null>(null)
  
  // 计算属性
  const hasMessages = computed(() => messages.value.length > 0)
  
  const formattedDuration = computed(() => {
    const minutes = Math.floor(recordingDuration.value / 60)
    const seconds = recordingDuration.value % 60
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
  })
  
  const latestMessage = computed(() => {
    return messages.value[messages.value.length - 1] || null
  })
  
  const speakerStats = computed(() => {
    const stats = new Map<string, { count: number; totalLength: number }>()
    
    messages.value.forEach(msg => {
      if (!stats.has(msg.speaker)) {
        stats.set(msg.speaker, { count: 0, totalLength: 0 })
      }
      const stat = stats.get(msg.speaker)!
      stat.count++
      stat.totalLength += msg.text.length
    })
    
    return Array.from(stats.entries()).map(([speaker, stat]) => ({
      speaker,
      messageCount: stat.count,
      averageLength: Math.round(stat.totalLength / stat.count),
      totalLength: stat.totalLength
    }))
  })
  
  // WebSocket操作
  const connectWebSocket = async (wsConfig?: Partial<WebSocketConfig>) => {
    if (wsConfig) {
      config.value = { ...config.value, ...wsConfig }
    }
    
    isConnecting.value = true
    connectionError.value = null
    
    try {
      // 检测环境
      const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
      const wsUrl = isLocal ? 'ws://127.0.0.1:26000' : 'wss://192.168.100.205:8989'
      
      websocket.value = new WebSocket(wsUrl)
      
      websocket.value.onopen = () => {
        isConnected.value = true
        isConnecting.value = false
        
        // 发送配置
        websocket.value?.send(JSON.stringify({
          type: 'config',
          data: config.value
        }))
      }
      
      websocket.value.onmessage = (event) => {
        const data = JSON.parse(event.data)
        handleWebSocketMessage(data)
      }
      
      websocket.value.onclose = () => {
        isConnected.value = false
        isConnecting.value = false
        websocket.value = null
      }
      
      websocket.value.onerror = (error) => {
        connectionError.value = '连接失败，请检查网络或服务器状态'
        isConnecting.value = false
        console.error('WebSocket error:', error)
      }
      
    } catch (error) {
      connectionError.value = '连接失败'
      isConnecting.value = false
      console.error('Connect error:', error)
    }
  }
  
  const disconnectWebSocket = () => {
    if (websocket.value) {
      websocket.value.close()
    }
    isConnected.value = false
    websocket.value = null
  }
  
  const sendAudioData = (audioData: ArrayBuffer) => {
    if (websocket.value && isConnected.value) {
      websocket.value.send(audioData)
    }
  }
  
  // 处理WebSocket消息
  const handleWebSocketMessage = (data: any) => {
    switch (data.type) {
      case 'transcript':
        const message: AudioMessage = {
          id: data.id || Date.now().toString(),
          speaker: data.speaker || '发言人',
          text: data.text || '',
          timestamp: data.timestamp || new Date().toLocaleTimeString(),
          isFinal: data.is_final || false
        }
        
        if (data.is_final) {
          addMessage(message)
          currentMessage.value = null
        } else {
          currentMessage.value = message
        }
        break
        
      case 'error':
        connectionError.value = data.message
        break
        
      case 'status':
        // 处理状态更新
        break
    }
  }
  
  // 消息管理
  const addMessage = (message: AudioMessage) => {
    messages.value.push(message)
  }
  
  const clearMessages = () => {
    messages.value = []
    currentMessage.value = null
  }
  
  const updateMessage = (id: string, updates: Partial<AudioMessage>) => {
    const index = messages.value.findIndex(m => m.id === id)
    if (index > -1) {
      messages.value[index] = { ...messages.value[index], ...updates }
    }
  }
  
  const removeMessage = (id: string) => {
    const index = messages.value.findIndex(m => m.id === id)
    if (index > -1) {
      messages.value.splice(index, 1)
    }
  }
  
  // 录制控制
  const startRecording = async () => {
    try {
      mediaStream.value = await navigator.mediaDevices.getUserMedia({
        audio: {
          deviceId: selectedDevice.value || undefined,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      })
      
      isRecording.value = true
      isPaused.value = false
      recordingDuration.value = 0
      
      // 开始计时
      startDurationTimer()
      
    } catch (error) {
      console.error('获取音频设备失败:', error)
      throw new Error('无法访问麦克风，请检查权限设置')
    }
  }
  
  const stopRecording = () => {
    if (mediaStream.value) {
      mediaStream.value.getTracks().forEach(track => track.stop())
      mediaStream.value = null
    }
    
    isRecording.value = false
    isPaused.value = false
    stopDurationTimer()
  }
  
  const pauseRecording = () => {
    isPaused.value = true
    stopDurationTimer()
  }
  
  const resumeRecording = () => {
    isPaused.value = false
    startDurationTimer()
  }
  
  // 计时器
  let durationTimer: number | null = null
  
  const startDurationTimer = () => {
    if (durationTimer) clearInterval(durationTimer)
    
    durationTimer = window.setInterval(() => {
      if (isRecording.value && !isPaused.value) {
        recordingDuration.value++
      }
    }, 1000)
  }
  
  const stopDurationTimer = () => {
    if (durationTimer) {
      clearInterval(durationTimer)
      durationTimer = null
    }
  }
  
  // 音频设备管理
  const loadAudioDevices = async () => {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices()
      audioDevices.value = devices.filter(device => device.kind === 'audioinput')
      
      if (audioDevices.value.length > 0 && !selectedDevice.value) {
        selectedDevice.value = audioDevices.value[0].deviceId
      }
    } catch (error) {
      console.error('获取音频设备列表失败:', error)
    }
  }
  
  // 配置管理
  const updateConfig = (newConfig: Partial<WebSocketConfig>) => {
    config.value = { ...config.value, ...newConfig }
    
    // 如果已连接，发送新配置
    if (websocket.value && isConnected.value) {
      websocket.value.send(JSON.stringify({
        type: 'config',
        data: config.value
      }))
    }
  }
  
  return {
    // 状态
    websocket,
    isConnected,
    isConnecting,
    connectionError,
    isRecording,
    isPaused,
    recordingDuration,
    messages,
    currentMessage,
    config,
    mediaStream,
    audioDevices,
    selectedDevice,
    audioLevel,
    frequencyData,
    
    // 计算属性
    hasMessages,
    formattedDuration,
    latestMessage,
    speakerStats,
    
    // 方法
    connectWebSocket,
    disconnectWebSocket,
    sendAudioData,
    addMessage,
    clearMessages,
    updateMessage,
    removeMessage,
    startRecording,
    stopRecording,
    pauseRecording,
    resumeRecording,
    loadAudioDevices,
    updateConfig
  }
}) 