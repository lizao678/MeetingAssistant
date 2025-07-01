import http from './http'

export interface Recording {
  id: string
  title: string
  description: string
  duration: string
  fileSize: string
  createTime: string
  updateTime: string
  status: 'completed' | 'processing' | 'failed'
  language: string
  speakerCount: number
  tags: string[]
  hasTranscript: boolean
  hasSummary: boolean
  preview: string
}

export interface RecordingFilter {
  search?: string
  status?: string
  dateRange?: [string, string]
  tags?: string[]
}

class RecordingService {
  // 获取录音列表
  async getRecordings(filter?: RecordingFilter): Promise<{
    data: Recording[]
    total: number
    page: number
    pageSize: number
  }> {
    return http.get('/api/recordings', { params: filter })
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

  // 删除录音
  async deleteRecording(id: string): Promise<void> {
    return http.delete(`/api/recordings/${id}`)
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
    return http.get(`/api/recordings/${id}/download`, {
      responseType: 'blob'
    })
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