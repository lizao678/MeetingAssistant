// 音频消息接口
export interface AudioMessage {
  id: number
  text: string
  speakerId: string
  speakerColor: string
  speakerNumber: string
  speakerClass: string
  timestamp: string
  confidence: number
  isNewLine: boolean
  segmentType: 'new_speaker' | 'pause' | 'continue' | 'traditional'
}

// 说话人信息接口
export interface SpeakerInfo {
  id: string
  color: string
  number: string
  className: string
}

// 录音状态类型
export type RecordingStatus = 'idle' | 'connecting' | 'recording' | 'paused' | 'stopped'

// WebSocket消息响应接口
export interface WSMessageResponse {
  code: number
  msg: string
  data: string
  speaker_id?: string
  is_new_line?: boolean
  segment_type?: string
  timestamp?: number
  confidence?: number
}

// 录音文件信息接口
export interface RecordingFile {
  id: number
  title: string
  duration: number // 毫秒
  size: number // 字节
  format: string
  created_at: string
  status: 'processing' | 'completed' | 'failed'
  file_path: string
}

// 会议总结接口
export interface MeetingSummary {
  id: number
  recording_id: number
  title: string
  keywords: string[]
  summary: string
  key_points: string[]
  action_items: string[]
  participants_count: number
  ai_model: string
  created_at: string
}

// 发言人总结接口
export interface SpeakerSummary {
  id: number
  speaker_id: string
  speaker_name: string
  summary: string
  key_opinions: string[]
  speaking_time_ratio: number
  total_duration: number
}

// 语音识别设置接口
export interface RecognitionSettings {
  language: 'auto' | 'zh' | 'en' | 'ja' | 'ko' | 'yue'
  speaker_verification: boolean
  smart_line_break: boolean
  chunk_size_ms: number
  pause_threshold_ms: number
}

// 环境配置接口
export interface EnvironmentConfig {
  host: string
  port: number
  protocol: 'ws' | 'wss'
  ssl: boolean
}

// 音频设备信息接口
export interface AudioDevice {
  deviceId: string
  label: string
  kind: 'audioinput' | 'audiooutput'
}

// 音频分析数据接口
export interface AudioAnalysis {
  volume: number
  frequency: number[]
  speaking_detected: boolean
  silence_duration: number
} 