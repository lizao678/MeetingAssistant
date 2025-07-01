import http from './http'

export interface SummaryData {
  keywords: string[]
  summary: string
  speakerSummaries: Array<{
    id: string
    name: string
    duration: string
    summary: string
  }>
  todos: string[]
  sentimentAnalysis?: {
    overall: 'positive' | 'neutral' | 'negative'
    details: Array<{
      speaker: string
      sentiment: 'positive' | 'neutral' | 'negative'
      confidence: number
    }>
  }
}

export interface TranscriptAnalysis {
  wordCount: number
  speakingTime: Array<{
    speaker: string
    duration: number
    percentage: number
  }>
  keyTopics: Array<{
    topic: string
    frequency: number
    relevance: number
  }>
  meetingEfficiency: {
    score: number
    suggestions: string[]
  }
}

class AIService {
  // 生成智能总结
  async generateSummary(recordingId: string, options: {
    includeKeywords?: boolean
    includeSpeakerSummary?: boolean
    includeTodos?: boolean
    includeSentiment?: boolean
  } = {}): Promise<{ taskId: string }> {
    return http.post(`/api/ai/summary/${recordingId}`, options)
  }

  // 获取智能总结结果
  async getSummary(recordingId: string): Promise<SummaryData> {
    return http.get(`/api/ai/summary/${recordingId}`)
  }

  // 分析转写文本
  async analyzeTranscript(recordingId: string): Promise<TranscriptAnalysis> {
    return http.get(`/api/ai/analysis/${recordingId}`)
  }

  // 提取关键词
  async extractKeywords(text: string, maxKeywords: number = 10): Promise<{
    keywords: Array<{
      word: string
      frequency: number
      relevance: number
    }>
  }> {
    return http.post('/api/ai/keywords', {
      text,
      maxKeywords
    })
  }

  // 情感分析
  async analyzeSentiment(text: string): Promise<{
    sentiment: 'positive' | 'neutral' | 'negative'
    confidence: number
    details: {
      positive: number
      neutral: number
      negative: number
    }
  }> {
    return http.post('/api/ai/sentiment', { text })
  }

  // 话题分类
  async classifyTopics(text: string): Promise<{
    topics: Array<{
      name: string
      confidence: number
      keywords: string[]
    }>
  }> {
    return http.post('/api/ai/topics', { text })
  }

  // 生成会议纪要
  async generateMeetingMinutes(recordingId: string, template?: string): Promise<{
    taskId: string
  }> {
    return http.post(`/api/ai/minutes/${recordingId}`, {
      template
    })
  }

  // 获取会议纪要
  async getMeetingMinutes(recordingId: string): Promise<{
    id: string
    title: string
    date: string
    participants: string[]
    agenda: string[]
    keyPoints: string[]
    decisions: string[]
    actionItems: Array<{
      task: string
      assignee?: string
      deadline?: string
      priority: 'high' | 'medium' | 'low'
    }>
    nextSteps: string[]
  }> {
    return http.get(`/api/ai/minutes/${recordingId}`)
  }

  // 智能搜索
  async semanticSearch(query: string, options: {
    recordingIds?: string[]
    timeRange?: [string, string]
    includeTranscript?: boolean
    includeSummary?: boolean
  } = {}): Promise<{
    results: Array<{
      recordingId: string
      title: string
      relevance: number
      matchedSegments: Array<{
        text: string
        timestamp: string
        speaker: string
      }>
    }>
  }> {
    return http.post('/api/ai/search', {
      query,
      ...options
    })
  }

  // 获取AI处理状态
  async getTaskStatus(taskId: string): Promise<{
    id: string
    status: 'pending' | 'processing' | 'completed' | 'failed'
    progress: number
    result?: any
    error?: string
  }> {
    return http.get(`/api/ai/tasks/${taskId}`)
  }

  // 语言检测
  async detectLanguage(text: string): Promise<{
    language: string
    confidence: number
    supportedLanguages: string[]
  }> {
    return http.post('/api/ai/detect-language', { text })
  }

  // 自动翻译
  async translateText(text: string, targetLanguage: string, sourceLanguage?: string): Promise<{
    translatedText: string
    sourceLanguage: string
    targetLanguage: string
    confidence: number
  }> {
    return http.post('/api/ai/translate', {
      text,
      targetLanguage,
      sourceLanguage
    })
  }

  // 智能标签建议
  async suggestTags(recordingId: string): Promise<{
    suggestions: Array<{
      tag: string
      confidence: number
      reason: string
    }>
  }> {
    return http.get(`/api/ai/tags/${recordingId}`)
  }

  // 会议质量评估
  async assessMeetingQuality(recordingId: string): Promise<{
    overallScore: number
    dimensions: {
      participation: number
      efficiency: number
      clarity: number
      engagement: number
    }
    insights: string[]
    recommendations: string[]
  }> {
    return http.get(`/api/ai/quality/${recordingId}`)
  }
}

export default new AIService() 