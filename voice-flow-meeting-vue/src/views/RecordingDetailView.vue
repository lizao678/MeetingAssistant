<template>
  <div class="recording-detail-view">
    <!-- 头部信息区 -->
    <div class="detail-header">
      <div class="header-left">
        <el-button 
          :icon="'ArrowLeft'" 
          @click="goBack"
          size="large"
          text
          class="back-button"
        >
          返回
        </el-button>
        <div class="title-section">
          <h1 class="recording-title">{{ recordingDetail.title }}</h1>
          <div class="meta-info">
            <el-tag type="info" size="small">{{ recordingDetail.language }}</el-tag>
            <span class="meta-item">{{ formatTime(recordingDetail.duration) }}</span>
            <span class="meta-item">{{ recordingDetail.createTime }}</span>
            <span class="meta-item">{{ recordingDetail.speakerCount }}人发言</span>
          </div>
        </div>
      </div>
      <div class="header-actions">
        <el-space>
          <el-button :icon="'Download'" @click="downloadRecording">下载录音</el-button>
          <el-button :icon="'Share'" @click="shareRecording">分享</el-button>
          <el-dropdown trigger="click">
            <el-button :icon="'MoreFilled'">更多</el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item :icon="'Edit'">编辑标题</el-dropdown-item>
                <el-dropdown-item :icon="'DocumentCopy'">导出文档</el-dropdown-item>
                <el-dropdown-item :icon="'Delete'" class="danger-item">删除录音</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </el-space>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-container">
      <el-skeleton animated>
        <template #template>
          <el-skeleton-item variant="text" style="width: 40%" />
          <el-skeleton-item variant="text" style="width: 20%" />
          <el-skeleton-item variant="rect" style="width: 100%; height: 200px" />
        </template>
      </el-skeleton>
    </div>

    <!-- 主内容区 -->
    <div v-else class="detail-content">
      <el-row :gutter="24">
        <!-- 左侧：智能速览 -->
        <el-col :span="8">
          <div class="sidebar-content">
            <!-- 关键词云 -->
            <el-card class="summary-card" shadow="never">
              <template #header>
                <div class="card-header">
                  <h3>关键词</h3>
                  <el-button text size="small" :icon="'Refresh'" @click="refreshKeywords">
                    刷新
                  </el-button>
                </div>
              </template>
              <div class="keywords-section">
                <div v-if="keywords.length === 0" class="empty-placeholder">
                  <el-icon size="48" color="#c0c4cc"><DocumentCopy /></el-icon>
                  <p>正在提取关键词...</p>
                </div>
                <div v-else class="keywords-cloud">
                  <el-tag
                    v-for="keyword in keywords"
                    :key="keyword.word"
                    :type="getKeywordType(keyword.score)"
                    :size="getKeywordSize(keyword.score)"
                    class="keyword-tag"
                    @click="highlightKeyword(keyword.word)"
                  >
                    {{ keyword.word }}
                    <span class="keyword-score">({{ keyword.count }})</span>
                  </el-tag>
                </div>
              </div>
            </el-card>

            <!-- 智能摘要 -->
            <el-card class="summary-card" shadow="never">
              <template #header>
                <div class="card-header">
                  <h3>智能摘要</h3>
                  <el-button text size="small" :icon="'Refresh'" @click="refreshSummary">
                    重新生成
                  </el-button>
                </div>
              </template>
              <div class="summary-content">
                <div v-if="!summary.content" class="empty-placeholder">
                  <el-icon size="48" color="#c0c4cc"><Reading /></el-icon>
                  <p>正在生成摘要...</p>
                </div>
                <div v-else>
                  <div class="summary-text">
                    {{ summary.content }}
                  </div>
                  <div class="summary-meta">
                    <el-rate 
                      v-model="summary.quality" 
                      :max="5" 
                      size="small"
                      text-color="#ff9900"
                      void-color="#c6d1de"
                      disabled
                    />
                    <span class="quality-text">摘要质量</span>
                  </div>
                </div>
              </div>
            </el-card>

            <!-- 章节速览 -->
            <el-card v-if="chapters.length > 0" class="summary-card" shadow="never">
              <template #header>
                <h3>章节速览</h3>
              </template>
              <div class="chapters-list">
                <div
                  v-for="(chapter, index) in chapters"
                  :key="index"
                  class="chapter-item"
                  @click="jumpToChapter(chapter.startTime)"
                >
                  <div class="chapter-time">{{ formatTime(chapter.startTime) }}</div>
                  <div class="chapter-title">{{ chapter.title }}</div>
                  <div class="chapter-summary">{{ chapter.summary }}</div>
                </div>
              </div>
            </el-card>
          </div>
        </el-col>

        <!-- 右侧：原文显示 -->
        <el-col :span="16">
          <el-card class="transcript-card" shadow="never">
            <template #header>
              <div class="card-header">
                <h3>转写原文</h3>
                <div class="transcript-controls">
                  <el-input
                    v-model="searchText"
                    placeholder="搜索内容..."
                    :prefix-icon="'Search'"
                    size="small"
                    style="width: 200px; margin-right: 12px;"
                    @input="handleSearch"
                  />
                  <el-button :icon="'CopyDocument'" size="small" @click="copyTranscript">
                    复制全文
                  </el-button>
                </div>
              </div>
            </template>
            
            <div ref="transcriptContainer" class="transcript-content">
              <div
                v-for="(segment, index) in filteredSegments"
                :key="segment.id"
                :id="`segment-${segment.id}`"
                class="transcript-segment"
                :class="{
                  'highlighted': highlightedSegment === segment.id,
                  'playing': currentPlayingSegment === segment.id
                }"
                @click="playSegment(segment)"
              >
                <div class="segment-meta">
                  <div class="speaker-info">
                    <el-avatar 
                      :size="32" 
                      :style="{ backgroundColor: segment.speakerColor }"
                    >
                      {{ segment.speakerNumber }}
                    </el-avatar>
                    <span class="speaker-name">{{ segment.speakerName }}</span>
                  </div>
                  <div class="segment-time">
                    {{ formatTime(segment.startTime) }} - {{ formatTime(segment.endTime) }}
                  </div>
                </div>
                <div class="segment-content">
                  <p v-html="segment.highlightedText || segment.text"></p>
                </div>
              </div>

              <!-- 空状态 -->
              <div v-if="filteredSegments.length === 0" class="empty-state">
                <el-empty description="没有找到匹配的内容">
                  <el-button @click="searchText = ''">清除搜索</el-button>
                </el-empty>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 底部音频播放器 -->
    <div class="audio-player-section">
      <!-- TODO: 集成AudioPlayer组件 -->
      <div class="audio-placeholder">
        <el-icon size="48" color="#c0c4cc"><Headphone /></el-icon>
        <p>音频播放器组件开发中...</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import recordingService from '@/services/recordingService'
import type { RecordingDetail, SpeechSegment, IntelligentSummary, Keyword } from '@/services/recordingService'
// import AudioPlayer from '../components/AudioPlayer.vue'

const route = useRoute()
const router = useRouter()

// 录音详情数据
const recordingDetail = ref({
  id: '',
  title: '',
  duration: 0,
  language: '',
  createTime: '',
  speakerCount: 0,
  audioUrl: '',
  status: 'processing' as 'processing' | 'completed' | 'failed'
})

// 关键词数据
const keywords = ref<Keyword[]>([])

// 摘要数据
const summary = ref<IntelligentSummary>({
  content: '',
  quality: 0,
  wordCount: 0,
  keyPoints: [],
  summaryType: 'meeting'
})

// 章节数据（基于AI分析生成）
const chapters = ref<Array<{
  title: string
  summary: string
  startTime: number
  endTime: number
}>>([])

// 转写段落数据（扩展SpeechSegment类型以适配模板）
interface ExtendedSegment extends SpeechSegment {
  highlightedText?: string
  text: string // 添加text字段以兼容模板
  speakerNumber: string // 添加speakerNumber字段
}

const segments = ref<ExtendedSegment[]>([])

// 加载状态
const loading = ref(true)
const recordingId = route.params.id as string

// 交互状态
const searchText = ref('')
const highlightedSegment = ref<number | null>(null)
const currentPlayingSegment = ref<number | null>(null)
const currentPlayTime = ref(0)
const transcriptContainer = ref<HTMLElement>()

// 过滤后的段落
const filteredSegments = computed(() => {
  if (!searchText.value.trim()) {
    return segments.value.map(segment => ({
      ...segment,
      highlightedText: ''
    }))
  }
  
  const searchTerm = searchText.value.trim().toLowerCase()
  return segments.value
    .filter(segment => segment.text.toLowerCase().includes(searchTerm))
    .map(segment => ({
      ...segment,
      highlightedText: segment.text.replace(
        new RegExp(`(${searchTerm})`, 'gi'),
        '<mark>$1</mark>'
      )
    }))
})

// 方法
const goBack = () => {
  router.back()
}

const getKeywordType = (score: number) => {
  if (score >= 0.8) return 'danger'
  if (score >= 0.6) return 'warning'
  if (score >= 0.4) return 'primary'
  return 'info'
}

const getKeywordSize = (score: number) => {
  if (score >= 0.8) return 'large'
  if (score >= 0.6) return 'default'
  return 'small'
}

const formatTime = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const highlightKeyword = (keyword: string) => {
  searchText.value = keyword
  handleSearch()
}

const handleSearch = () => {
  // 搜索逻辑已在computed中处理
}

const playSegment = (segment: any) => {
  currentPlayingSegment.value = segment.id
  // TODO: 触发音频播放器跳转到指定时间
}

const jumpToChapter = (startTime: number) => {
  currentPlayTime.value = startTime
  // TODO: 触发音频播放器跳转
}

const copyTranscript = async () => {
  try {
    const fullText = segments.value
      .map(segment => `${segment.speakerName}: ${segment.text}`)
      .join('\n\n')
    
    await navigator.clipboard.writeText(fullText)
    ElMessage.success('转写内容已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败，请手动选择复制')
  }
}

const refreshKeywords = () => {
  ElMessage.info('正在重新提取关键词...')
  // TODO: 调用API重新生成关键词
}

const refreshSummary = async () => {
  try {
    const loading = ElLoading.service({
      lock: true,
      text: '正在重新生成智能摘要...',
      background: 'rgba(0, 0, 0, 0.7)'
    })
    
    const response = await recordingService.regenerateSummary(recordingId, summary.value.summaryType)
    
    if (response.success && response.data) {
      summary.value = response.data
      ElMessage.success('摘要已重新生成')
    } else {
      throw new Error('生成摘要失败')
    }
    
    loading.close()
  } catch (error: any) {
    ElMessage.error(`重新生成摘要失败: ${error.message || '未知错误'}`)
    console.error('重新生成摘要失败:', error)
  }
}

const downloadRecording = async () => {
  try {
    ElMessage.info('开始下载录音文件...')
    
    const blob = await recordingService.downloadRecording(recordingId)
    
    // 创建下载链接
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${recordingDetail.value.title || '录音文件'}.wav`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)
    
    ElMessage.success('下载完成')
  } catch (error: any) {
    ElMessage.error(`下载失败: ${error.message || '未知错误'}`)
    console.error('下载录音失败:', error)
  }
}

const shareRecording = () => {
  ElMessage.info('生成分享链接...')
  // TODO: 实现分享功能
}

// 音频播放器事件处理
const handleTimeUpdate = (time: number) => {
  currentPlayTime.value = time
  
  // 自动高亮当前播放的段落
  const currentSegment = segments.value.find(segment => 
    time >= segment.startTime && time <= segment.endTime
  )
  
  if (currentSegment && currentSegment.id !== undefined) {
    highlightedSegment.value = currentSegment.id
    
    // 自动滚动到当前段落
    nextTick(() => {
      const element = document.getElementById(`segment-${currentSegment.id}`)
      if (element && transcriptContainer.value) {
        element.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
    })
  }
}

const handleSegmentPlay = (segmentId: number) => {
  currentPlayingSegment.value = segmentId
}

const handlePlayStateChange = (isPlaying: boolean) => {
  if (!isPlaying) {
    currentPlayingSegment.value = null
  }
}

// 加载录音详情数据
const loadRecordingDetail = async () => {
  if (!recordingId) {
    ElMessage.error('录音ID不存在')
    router.push('/recordings')
    return
  }

  try {
    loading.value = true
    console.log('正在加载录音详情:', recordingId)
    
    // 调用API获取录音详情
    const response = await recordingService.getRecordingDetail(recordingId)
    
    if (response.success && response.data) {
      const { recording, segments: rawSegments, summary: rawSummary, keywords: rawKeywords } = response.data
      
      // 设置录音基本信息
      recordingDetail.value = {
        id: recording.id,
        title: recording.title || `录音记录 ${recording.createTime}`,
        duration: recording.duration,
        language: recording.language,
        createTime: recording.createTime,
        speakerCount: recording.speakerCount,
        audioUrl: `/api/recordings/${recording.id}/download`,
        status: recording.status
      }
      
      // 转换段落数据格式（后端已返回驼峰格式，直接使用）
      segments.value = rawSegments.map((segment: any, index) => ({
        ...segment,
        text: segment.content, // 添加text字段以兼容模板
        speakerNumber: (segment.speakerId || '').replace(/[^0-9]/g, '') || String(index + 1), // 提取数字作为发言人编号
        highlightedText: ''
      }))
      
      // 设置摘要数据（后端已返回驼峰格式，直接使用）
      if (rawSummary) {
        summary.value = rawSummary
      }
      
      // 设置关键词数据
      keywords.value = rawKeywords || []
      
      // 生成章节数据（基于发言人变化和时间间隔）
      generateChapters()
      
      console.log('录音详情加载完成:', recording.title)
    } else {
      throw new Error('获取录音详情失败')
    }
  } catch (error: any) {
    console.error('加载录音详情失败:', error)
    
    if (error.response?.status === 404) {
      ElMessage.error('录音记录不存在')
      router.push('/recordings')
    } else if (error.response?.status === 500) {
      ElMessage.error('服务器错误，请稍后重试')
    } else {
      ElMessage.error(`加载失败: ${error.message || '未知错误'}`)
    }
  } finally {
    loading.value = false
  }
}

// 生成章节数据
const generateChapters = () => {
  if (segments.value.length === 0) return
  
  const chapterDuration = 300 // 5分钟一个章节
  const totalDuration = Math.max(...segments.value.map(s => s.endTime))
  const chapterCount = Math.ceil(totalDuration / chapterDuration)
  
  chapters.value = Array.from({ length: chapterCount }, (_, index) => {
    const startTime = index * chapterDuration
    const endTime = Math.min((index + 1) * chapterDuration, totalDuration)
    
    // 获取该时间段内的主要发言人和内容
    const segmentsInChapter = segments.value.filter(s => 
      s.startTime >= startTime && s.startTime < endTime
    )
    
    const mainSpeaker = segmentsInChapter.length > 0 ? segmentsInChapter[0].speakerName : '发言人'
    const contentPreview = segmentsInChapter.slice(0, 2).map(s => s.text).join(' ').substring(0, 50)
    
    return {
      title: `第${index + 1}部分 - ${mainSpeaker}`,
      summary: contentPreview + (contentPreview.length >= 50 ? '...' : ''),
      startTime,
      endTime
    }
  })
}

// 生命周期
onMounted(() => {
  loadRecordingDetail()
})

onUnmounted(() => {
  // 清理资源
})
</script>

<style scoped>
.recording-detail-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f7fa;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 20px 24px;
  background: white;
  border-bottom: 1px solid #e4e7ed;
  gap: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
}

.back-button {
  padding: 8px !important;
  color: #606266;
}

.title-section {
  flex: 1;
}

.recording-title {
  margin: 0 0 8px 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.meta-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.meta-item {
  color: #909399;
  font-size: 14px;
}

.header-actions {
  flex-shrink: 0;
}

.loading-container {
  flex: 1;
  padding: 24px;
}

.danger-item {
  color: #f56c6c;
}

.detail-content {
  flex: 1;
  padding: 24px;
  overflow: hidden;
}

.sidebar-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: 100%;
}

.summary-card {
  border-radius: 12px;
  border: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.empty-placeholder {
  text-align: center;
  padding: 40px 20px;
  color: #909399;
}

.empty-placeholder p {
  margin: 12px 0 0 0;
  font-size: 14px;
}

.keywords-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.keyword-tag {
  cursor: pointer;
  transition: all 0.3s;
}

.keyword-tag:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}

.keyword-score {
  font-size: 12px;
  opacity: 0.7;
  margin-left: 4px;
}

.summary-content {
  line-height: 1.6;
}

.summary-text {
  margin-bottom: 16px;
  color: #606266;
  font-size: 14px;
}

.summary-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.quality-text {
  font-size: 12px;
  color: #909399;
}

.chapters-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chapter-item {
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.chapter-item:hover {
  background: #e8f4ff;
  border-color: #409eff;
}

.chapter-time {
  font-size: 12px;
  color: #409eff;
  font-weight: 600;
  margin-bottom: 4px;
}

.chapter-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 4px;
}

.chapter-summary {
  font-size: 12px;
  color: #606266;
}

.transcript-card {
  border-radius: 12px;
  border: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  height: 100%;
}

.transcript-controls {
  display: flex;
  align-items: center;
}

.transcript-content {
  max-height: calc(100vh - 400px);
  overflow-y: auto;
  padding-right: 8px;
}

.transcript-segment {
  padding: 16px;
  margin-bottom: 12px;
  background: #f8f9fa;
  border-radius: 12px;
  border: 2px solid transparent;
  cursor: pointer;
  transition: all 0.3s;
}

.transcript-segment:hover {
  background: #e8f4ff;
  border-color: #c6d7f0;
}

.transcript-segment.highlighted {
  background: #fff7e6;
  border-color: #ffa940;
}

.transcript-segment.playing {
  background: #e6f7ff;
  border-color: #409eff;
}

.segment-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.speaker-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.speaker-name {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
}

.segment-time {
  font-size: 12px;
  color: #909399;
  font-family: 'SF Mono', 'Monaco', 'Menlo', 'Courier New', monospace;
}

.segment-content {
  line-height: 1.6;
  color: #606266;
}

.segment-content p {
  margin: 0;
}

.segment-content :deep(mark) {
  background: #fff2cc;
  color: #d46b08;
  padding: 0 2px;
  border-radius: 2px;
}

.audio-player-section {
  background: white;
  border-top: 1px solid #e4e7ed;
  padding: 16px 24px;
}

.audio-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #909399;
  text-align: center;
}

.audio-placeholder p {
  margin: 12px 0 0 0;
  font-size: 14px;
}

.empty-state {
  padding: 60px 20px;
  text-align: center;
}

.danger-item {
  color: #f56c6c;
}

:deep(.el-card__header) {
  padding: 16px 20px;
  border-bottom: 1px solid #f0f0f0;
}

:deep(.el-card__body) {
  padding: 20px;
}
</style>
