import http from './http'

interface AudioServiceInterface {
  // WebSocket实时音频流处理
  createWebSocketConnection(options: {
    language: string
    enableSpeakerRecognition: boolean
    enableSmartBreaks: boolean
  }): Promise<WebSocket>
  
  // 音频文件上传和处理
  uploadAudio(file: File, options?: {
    language?: string
    speakerCount?: number
  }): Promise<{
    id: string
    status: string
    message: string
  }>
  
  // 获取转写结果
  getTranscription(audioId: string): Promise<{
    id: string
    text: string
    segments: Array<{
      speaker: string
      startTime: number
      endTime: number
      text: string
    }>
    status: string
  }>
  
  // 获取音频文件信息
  getAudioInfo(audioId: string): Promise<{
    id: string
    filename: string
    duration: number
    fileSize: number
    format: string
    sampleRate: number
  }>
}

class AudioService implements AudioServiceInterface {
  async createWebSocketConnection(options: {
    language: string
    enableSpeakerRecognition: boolean
    enableSmartBreaks: boolean
  }): Promise<WebSocket> {
    // 检测环境（本地开发 vs 生产环境）
    const isLocal = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    const wsUrl = isLocal ? 'ws://127.0.0.1:26000' : 'wss://192.168.100.205:8989'
    
    const ws = new WebSocket(wsUrl)
    
    return new Promise((resolve, reject) => {
      ws.onopen = () => {
        // 发送配置信息
        ws.send(JSON.stringify({
          type: 'config',
          data: options
        }))
        resolve(ws)
      }
      
      ws.onerror = (error) => {
        reject(error)
      }
      
      // 设置超时
      setTimeout(() => {
        if (ws.readyState !== WebSocket.OPEN) {
          reject(new Error('WebSocket连接超时'))
        }
      }, 5000)
    })
  }

  async uploadAudio(file: File, options = {}): Promise<{
    id: string
    status: string
    message: string
  }> {
    const formData = new FormData()
    formData.append('audio', file)
    formData.append('options', JSON.stringify(options))
    
    return http.post('/api/audio/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  }

  async getTranscription(audioId: string): Promise<{
    id: string
    text: string
    segments: Array<{
      speaker: string
      startTime: number
      endTime: number
      text: string
    }>
    status: string
  }> {
    return http.get(`/api/audio/${audioId}/transcription`)
  }

  async getAudioInfo(audioId: string): Promise<{
    id: string
    filename: string
    duration: number
    fileSize: number
    format: string
    sampleRate: number
  }> {
    return http.get(`/api/audio/${audioId}/info`)
  }
}

export default new AudioService() 