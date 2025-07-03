import http from './http'

// 发言人相关的类型定义
export interface FrequentSpeaker {
  id: number
  name: string
  color: string
  useCount: number
  createdAt: string
  lastUsedAt: string
}

export interface FrequentSpeakerRequest {
  name: string
  color?: string
}

export interface UpdateFrequentSpeakerRequest {
  name?: string
  color?: string
}

export interface UpdateSpeakerRequest {
  new_name: string
  setting_type: 'single' | 'global'
  frequent_speaker_id?: number
}

export interface SpeakerSettingsLog {
  id: number
  speakerId: string
  oldName: string | null
  newName: string
  settingType: string
  frequentSpeakerId: number | null
  createdAt: string
}

export interface ApiResponse<T> {
  success: boolean
  data?: T
  message?: string
  total?: number
}

/**
 * 发言人服务API
 */
class SpeakerService {
  /**
   * 获取常用发言人列表
   */
  async getFrequentSpeakers(): Promise<FrequentSpeaker[]> {
    try {
      const response = await http.get<ApiResponse<FrequentSpeaker[]>>('/api/speakers/frequent')
      return response.data.data || []
    } catch (error) {
      console.error('获取常用发言人失败:', error)
      throw error
    }
  }

  /**
   * 添加常用发言人
   */
  async addFrequentSpeaker(speaker: FrequentSpeakerRequest): Promise<FrequentSpeaker> {
    try {
      const response = await http.post<ApiResponse<FrequentSpeaker>>('/api/speakers/frequent', speaker)
      if (!response.data.data) {
        throw new Error(response.data.message || '添加失败')
      }
      return response.data.data
    } catch (error) {
      console.error('添加常用发言人失败:', error)
      throw error
    }
  }

  /**
   * 更新常用发言人
   */
  async updateFrequentSpeaker(speakerId: number, updates: UpdateFrequentSpeakerRequest): Promise<void> {
    try {
      await http.put(`/api/speakers/frequent/${speakerId}`, updates)
    } catch (error) {
      console.error('更新常用发言人失败:', error)
      throw error
    }
  }

  /**
   * 删除常用发言人
   */
  async deleteFrequentSpeaker(speakerId: number): Promise<void> {
    try {
      await http.delete(`/api/speakers/frequent/${speakerId}`)
    } catch (error) {
      console.error('删除常用发言人失败:', error)
      throw error
    }
  }

  /**
   * 更新录音中的发言人信息
   */
  async updateSpeakerInRecording(
    recordingId: string, 
    speakerId: string, 
    updates: UpdateSpeakerRequest
  ): Promise<void> {
    try {
      await http.post(`/api/recordings/${recordingId}/speakers/${speakerId}/update`, updates)
    } catch (error) {
      console.error('更新录音中发言人失败:', error)
      throw error
    }
  }

  /**
   * 获取发言人设置日志
   */
  async getSpeakerSettingsLog(recordingId: string): Promise<SpeakerSettingsLog[]> {
    try {
      const response = await http.get<ApiResponse<SpeakerSettingsLog[]>>(
        `/api/recordings/${recordingId}/speakers/settings-log`
      )
      return response.data.data || []
    } catch (error) {
      console.error('获取发言人设置日志失败:', error)
      throw error
    }
  }
}

export default new SpeakerService() 