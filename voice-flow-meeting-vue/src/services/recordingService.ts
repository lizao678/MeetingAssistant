import http from './http'

export interface Recording {
  id: string
  title: string
  description?: string
  duration: number // 改为数字类型，单位秒
  fileSize?: string
  createTime: string
  updateTime: string
  status: 'completed' | 'processing' | 'failed'
  language: string
  speakerCount: number
  tags?: string[]
  hasTranscript?: boolean
  hasSummary?: boolean
  preview?: string
  filePath?: string
  options?: Record<string, any>
}

// 发言段落接口
export interface SpeechSegment {
  id?: number
  speakerId: string
  speakerName: string
  speakerColor: string
  content: string
  startTime: number
  endTime: number
  confidence?: number
}

// 智能摘要接口
export interface IntelligentSummary {
  content: string
  quality: number
  wordCount: number
  keyPoints: string[]
  compressionRatio?: number
  summaryType: string
  createTime?: string
}

// 关键词接口
export interface Keyword {
  word: string
  count: number
  score: number
  source: string
}

// 录音详情接口
export interface RecordingDetail {
  recording: Recording
  segments: SpeechSegment[]
  summary: IntelligentSummary | null
  keywords: Keyword[]
}

// 录音处理请求接口
export interface RecordingProcessRequest {
  audioFile: File
  speakerCount: number
  language: string
  smartPunctuation: boolean
  numberConversion: boolean
  generateSummary: boolean
  summaryType: string
}

// 录音处理响应接口
export interface RecordingProcessResponse {
  success: boolean
  recording_id?: string  // 后端返回的字段名是下划线格式
  message: string
  duration?: number
  error?: string
}

export interface RecordingFilter {
  search?: string
  status?: string
  dateRange?: [string, string]
  tags?: string[]
}

class RecordingService {
  // 处理录音文件（新API）
  async processRecording(
    data: RecordingProcessRequest, 
    onProgress?: (progress: number) => void
  ): Promise<RecordingProcessResponse> {
    const formData = new FormData()
    formData.append('audio_file', data.audioFile)
    formData.append('speaker_count', data.speakerCount.toString())
    formData.append('language', data.language)
    formData.append('smart_punctuation', data.smartPunctuation.toString())
    formData.append('number_conversion', data.numberConversion.toString())
    formData.append('generate_summary', data.generateSummary.toString())
    formData.append('summary_type', data.summaryType)

    return http.post('/api/recordings/process', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percentage = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(percentage)
        }
      }
    })
  }

  // 获取录音处理状态
  async getRecordingStatus(recordingId: string): Promise<{
    recordingId: string
    status: string
    title: string
    duration?: number
    createTime: string
  }> {
    return http.get(`/api/recordings/${recordingId}/status`)
  }

  // 获取录音完整详情（新API）
  async getRecordingDetail(recordingId: string): Promise<{
    success: boolean
    data: RecordingDetail
  }> {
    return http.get(`/api/recordings/${recordingId}/detail`)
  }

  // 重新生成摘要
  async regenerateSummary(recordingId: string, summaryType: string = 'meeting'): Promise<{
    success: boolean
    data: any
  }> {
    return http.post(`/api/recordings/${recordingId}/regenerate-summary`, {
      summary_type: summaryType
    })
  }

  // 获取录音列表
  async getRecordings(filter?: RecordingFilter & { page?: number; page_size?: number }): Promise<{
    success: boolean
    data: {
      recordings: Recording[]
      total: number
      page: number
      pageSize: number
      totalPages: number
    }
  }> {
    // 正确的参数处理：先展开filter，再设置默认值，避免参数冲突
    const params = {
      ...filter,
      page: filter?.page || 1,
      page_size: filter?.page_size || 12
    }
    return http.get('/api/recordings', { params })
  }

  // 获取单个录音详情
  async getRecording(id: string): Promise<Recording> {
    return http.get(`/api/recordings/${id}`)
  }

  // 创建新录音记录
  async createRecording(data: {
    title: string
    description?: string
    language: string
    audioFile?: File
  }): Promise<Recording> {
    const formData = new FormData()
    formData.append('title', data.title)
    if (data.description) formData.append('description', data.description)
    formData.append('language', data.language)
    if (data.audioFile) formData.append('audioFile', data.audioFile)

    return http.post('/api/recordings', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  }

  // 更新录音信息
  async updateRecording(id: string, data: Partial<Recording>): Promise<Recording> {
    return http.put(`/api/recordings/${id}`, data)
  }



  // 获取录音转写结果
  async getTranscript(id: string): Promise<{
    id: string
    segments: Array<{
      id: string
      speaker: string
      startTime: string
      endTime: string
      text: string
    }>
    status: string
  }> {
    return http.get(`/api/recordings/${id}/transcript`)
  }

  // 获取录音智能总结
  async getSummary(id: string): Promise<{
    id: string
    keywords: string[]
    summary: string
    speakerSummaries: Array<{
      id: string
      name: string
      duration: string
      summary: string
    }>
    todos: string[]
    status: string
  }> {
    return http.get(`/api/recordings/${id}/summary`)
  }

  // 生成智能总结
  async generateSummary(id: string): Promise<{ taskId: string }> {
    return http.post(`/api/recordings/${id}/generate-summary`)
  }

  // 下载录音文件
  async downloadRecording(id: string): Promise<Blob> {
    // 直接使用axios而不通过拦截器，因为拦截器会修改blob响应
    const axios = (await import('axios')).default
    const response = await axios.get(`${http.defaults.baseURL}/api/recordings/${id}/download`, {
      responseType: 'blob'
    })
    return response.data
  }

  // 删除录音（更新）
  async deleteRecording(id: string): Promise<{
    success: boolean
    message: string
  }> {
    return http.delete(`/api/recordings/${id}`)
  }

  // 离线重新处理录音（高精度）
  async offlineReprocessRecording(id: string): Promise<{
    success: boolean
    message: string
    recording_id?: string
  }> {
    return http.post(`/api/recordings/${id}/offline-reprocess`)
  }

  // 获取离线处理状态
  async getOfflineProcessingStatus(id: string): Promise<{
    recording_id: string
    status: string
    has_offline_processed: boolean
    can_reprocess: boolean
  }> {
    return http.get(`/api/recordings/${id}/offline-status`)
  }

  // 搜索录音
  async searchRecordings(query: string): Promise<Recording[]> {
    return http.get('/api/recordings/search', { params: { q: query } })
  }

  // 获取统计信息
  async getStatistics(): Promise<{
    totalRecordings: number
    totalDuration: string
    totalSize: string
    recentActivity: Array<{
      date: string
      count: number
    }>
  }> {
    return http.get('/api/recordings/statistics')
  }


}

export default new RecordingService() 