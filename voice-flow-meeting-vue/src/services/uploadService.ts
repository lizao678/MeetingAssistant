import http from './http'

export interface UploadProgress {
  loaded: number
  total: number
  percentage: number
}

export interface UploadResult {
  id: string
  filename: string
  url: string
  size: number
  type: string
}

class UploadService {
  // 上传单个文件
  async uploadFile(
    file: File, 
    onProgress?: (progress: UploadProgress) => void
  ): Promise<UploadResult> {
    const formData = new FormData()
    formData.append('file', file)

    return http.post('/api/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percentage = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress({
            loaded: progressEvent.loaded,
            total: progressEvent.total,
            percentage
          })
        }
      }
    })
  }

  // 批量上传文件
  async uploadFiles(
    files: File[],
    onProgress?: (index: number, progress: UploadProgress) => void
  ): Promise<UploadResult[]> {
    const results: UploadResult[] = []
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i]
      try {
        const result = await this.uploadFile(file, (progress) => {
          if (onProgress) {
            onProgress(i, progress)
          }
        })
        results.push(result)
      } catch (error) {
        console.error(`文件 ${file.name} 上传失败:`, error)
        throw error
      }
    }
    
    return results
  }

  // 检查文件类型和大小
  validateFile(file: File, options: {
    maxSize?: number // 字节
    allowedTypes?: string[] // MIME类型
  } = {}): { valid: boolean; error?: string } {
    const { maxSize = 100 * 1024 * 1024, allowedTypes = [] } = options // 默认100MB

    if (maxSize && file.size > maxSize) {
      return {
        valid: false,
        error: `文件大小不能超过 ${Math.round(maxSize / 1024 / 1024)}MB`
      }
    }

    if (allowedTypes.length > 0 && !allowedTypes.includes(file.type)) {
      return {
        valid: false,
        error: `不支持的文件类型: ${file.type}`
      }
    }

    return { valid: true }
  }

  // 获取支持的音频格式
  getSupportedAudioFormats(): string[] {
    return [
      'audio/wav',
      'audio/mp3',
      'audio/mpeg',
      'audio/flac',
      'audio/aac',
      'audio/ogg',
      'audio/webm',
      'video/mp4',
      'video/webm',
      'video/avi',
      'video/mov'
    ]
  }

  // 预处理音频文件（获取基本信息）
  async getAudioInfo(file: File): Promise<{
    duration: number
    size: number
    format: string
    sampleRate?: number
  }> {
    return new Promise((resolve, reject) => {
      const audio = new Audio()
      const url = URL.createObjectURL(file)
      
      audio.onloadedmetadata = () => {
        URL.revokeObjectURL(url)
        resolve({
          duration: audio.duration,
          size: file.size,
          format: file.type,
        })
      }
      
      audio.onerror = () => {
        URL.revokeObjectURL(url)
        reject(new Error('无法读取音频文件信息'))
      }
      
      audio.src = url
    })
  }

  // 分块上传大文件
  async uploadLargeFile(
    file: File,
    chunkSize: number = 1024 * 1024, // 1MB chunks
    onProgress?: (progress: UploadProgress) => void
  ): Promise<UploadResult> {
    const totalChunks = Math.ceil(file.size / chunkSize)
    const uploadId = Date.now().toString()
    
    // 初始化分块上传
    await http.post('/api/upload/init', {
      filename: file.name,
      size: file.size,
      uploadId,
      totalChunks
    })

    // 上传每个分块
    for (let i = 0; i < totalChunks; i++) {
      const start = i * chunkSize
      const end = Math.min(start + chunkSize, file.size)
      const chunk = file.slice(start, end)
      
      const formData = new FormData()
      formData.append('chunk', chunk)
      formData.append('uploadId', uploadId)
      formData.append('chunkIndex', i.toString())
      
      await http.post('/api/upload/chunk', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        }
      })
      
      if (onProgress) {
        onProgress({
          loaded: end,
          total: file.size,
          percentage: Math.round((end / file.size) * 100)
        })
      }
    }

    // 完成上传
    return http.post('/api/upload/complete', {
      uploadId,
      filename: file.name
    })
  }
}

export default new UploadService() 