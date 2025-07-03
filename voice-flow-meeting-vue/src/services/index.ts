// 服务层统一导出
export { default as audioService } from './audioService'
export { default as recordingService } from './recordingService'
export { default as uploadService } from './uploadService'
export { default as aiService } from './aiService'
export { default as speakerService } from './speakerService'
export { default as http } from './http'

// 导出类型定义
export type { Recording, RecordingFilter } from './recordingService'
export type { UploadProgress, UploadResult } from './uploadService'
export type { SummaryData, TranscriptAnalysis } from './aiService' 
export type { 
  FrequentSpeaker, 
  FrequentSpeakerRequest, 
  UpdateFrequentSpeakerRequest, 
  UpdateSpeakerRequest,
  SpeakerSettingsLog 
} from './speakerService' 