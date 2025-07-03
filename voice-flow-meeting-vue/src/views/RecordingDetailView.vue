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
          <el-button 
            v-if="aiProcessing" 
            type="warning" 
            :icon="'CircleClose'"
            @click="manualStopPolling"
          >
            停止AI处理
          </el-button>
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
      <!-- 关键词区域 -->
      <div class="section keywords-section">
        <div class="section-header">
          <h3>关键词</h3>
          <!-- <el-button text size="small" :icon="'Refresh'" @click="refreshKeywords">
            刷新
          </el-button> -->
        </div>
        <div class="section-content">
          <!-- AI处理中的loading状态 -->
          <div v-if="keywordsLoading" class="loading-placeholder">
            <el-skeleton animated>
              <template #template>
                <div style="display: flex; flex-wrap: wrap; gap: 8px;">
                  <el-skeleton-item v-for="i in 6" :key="i" variant="button" style="width: 60px; height: 24px; border-radius: 12px;" />
                </div>
              </template>
            </el-skeleton>
            <p class="loading-text">
              <el-icon class="is-loading"><Loading /></el-icon>
              AI正在提取关键词...
            </p>
          </div>
          <!-- 空状态 -->
          <div v-else-if="keywords.length === 0" class="empty-placeholder">
            <el-icon size="48" color="#c0c4cc"><DocumentCopy /></el-icon>
            <p>暂无关键词数据</p>
          </div>
          <!-- 关键词云 -->
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
      </div>

      <!-- 智能摘要区域 -->
      <div class="section summary-section">
        <div class="section-header">
          <h3>智能摘要</h3>
          <el-button text size="small" :icon="'Refresh'" @click="refreshSummary">
            重新生成
          </el-button>
        </div>
        <div class="section-content">
          <!-- AI处理中的loading状态 -->
          <div v-if="summaryLoading" class="loading-placeholder">
            <el-skeleton animated>
              <template #template>
                <el-skeleton-item variant="text" style="width: 100%" />
                <el-skeleton-item variant="text" style="width: 80%" />
                <el-skeleton-item variant="text" style="width: 90%" />
                <el-skeleton-item variant="text" style="width: 60%" />
              </template>
            </el-skeleton>
            <p class="loading-text">
              <el-icon class="is-loading"><Loading /></el-icon>
              AI正在生成智能摘要...
            </p>
          </div>
          <!-- 空状态 -->
          <div v-else-if="!summary.content" class="empty-placeholder">
            <el-icon size="48" color="#c0c4cc"><Reading /></el-icon>
            <p>暂无摘要数据</p>
          </div>
          <!-- 摘要内容 -->
          <div v-else class="summary-wrapper">
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
      </div>

      <!-- 章节速览区域 -->
      <div v-if="chaptersLoading || chapters.length > 0" class="section chapters-section">
        <div class="section-header">
          <h3>章节速览</h3>
        </div>
        <div class="section-content">
          <!-- AI处理中的loading状态 -->
          <div v-if="chaptersLoading" class="loading-placeholder">
            <el-skeleton animated>
              <template #template>
                <div v-for="i in 3" :key="i" style="margin-bottom: 16px;">
                  <el-skeleton-item variant="text" style="width: 30%; height: 14px;" />
                  <el-skeleton-item variant="text" style="width: 60%; height: 16px; margin-top: 4px;" />
                  <el-skeleton-item variant="text" style="width: 80%; height: 12px; margin-top: 4px;" />
                </div>
              </template>
            </el-skeleton>
            <p class="loading-text">
              <el-icon class="is-loading"><Loading /></el-icon>
              正在生成章节速览...
            </p>
          </div>
          <!-- 章节列表 -->
          <div v-else class="chapters-list">
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
        </div>
      </div>

      <!-- 转写原文区域 -->
      <div class="section transcript-section">
        <div class="section-header">
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
        <div class="section-content">
          <!-- 转写原文loading状态 -->
          <div v-if="transcriptLoading" class="loading-placeholder">
            <el-skeleton animated>
              <template #template>
                <div v-for="i in 4" :key="i" style="margin-bottom: 20px;">
                  <div style="display: flex; align-items: center; margin-bottom: 8px;">
                    <el-skeleton-item variant="circle" style="width: 32px; height: 32px; margin-right: 12px;" />
                    <el-skeleton-item variant="text" style="width: 80px; height: 16px;" />
                    <el-skeleton-item variant="text" style="width: 120px; height: 14px; margin-left: auto;" />
                  </div>
                  <el-skeleton-item variant="text" style="width: 100%; height: 16px;" />
                  <el-skeleton-item variant="text" style="width: 80%; height: 16px; margin-top: 4px;" />
                </div>
              </template>
            </el-skeleton>
            <p class="loading-text">
              <el-icon class="is-loading"><Loading /></el-icon>
              正在加载转写内容...
            </p>
          </div>
          
          <!-- 空状态 -->
          <div v-else-if="segments.length === 0" class="empty-placeholder">
            <el-icon size="48" color="#c0c4cc"><ChatDotRound /></el-icon>
            <p>暂无转写内容</p>
          </div>
          
          <!-- 转写内容 -->
          <div v-else ref="transcriptContainer" class="transcript-content">
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
                    class="speaker-avatar"
                    @click.stop="openSpeakerSetting(segment)"
                  >
                    {{ getSpeakerAvatarText(segment) }}
                  </el-avatar>
                  <span class="speaker-name" @click.stop="openSpeakerSetting(segment)">
                    {{ segment.speakerName }}
                  </span>
                </div>
                <div class="segment-time">
                  {{ formatTime(segment.startTime) }} - {{ formatTime(segment.endTime) }}
                </div>
              </div>
              <div class="segment-content">
                <p v-html="segment.highlightedText || segment.text"></p>
              </div>
            </div>

            <!-- 搜索无结果状态 -->
            <div v-if="filteredSegments.length === 0" class="empty-state">
              <el-empty description="没有找到匹配的内容">
                <el-button @click="searchText = ''">清除搜索</el-button>
              </el-empty>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- AI处理状态指示器 -->
    <div v-if="aiProcessing" class="processing-indicator">
      <div class="processing-content">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span class="processing-text">
          AI正在处理中... (第{{ pollingAttempts }}次检查, 已运行{{ Math.round((Date.now() - pollingStartTime) / 1000) }}秒)
        </span>
        <el-button 
          type="text" 
          size="small" 
          :icon="'CircleClose'"
          @click="manualStopPolling"
        >
          停止
        </el-button>
      </div>
      <el-progress 
        :percentage="Math.min((pollingAttempts / maxPollingAttempts) * 100, 100)" 
        :show-text="false"
        :stroke-width="2"
        color="#409eff"
      />
    </div>

    <!-- 底部音频播放器 -->
    <div v-if="recordingDetail.audioUrl" class="audio-player-section">
      <AudioPlayer
        :audio-url="recordingDetail.audioUrl"
        :segments="audioSegments"
        :current-time="currentPlayTime"
        @time-update="handleTimeUpdate"
        @segment-play="handleSegmentPlay"
        @play-state-change="handlePlayStateChange"
      />
    </div>
    <div v-else class="audio-player-placeholder">
      <div class="placeholder-content">
        <el-icon><Loading /></el-icon>
        <span>正在加载音频播放器...</span>
      </div>
    </div>

    <!-- 发言人设置对话框 -->
    <SpeakerSettingDialog
      v-model="showSpeakerSetting"
      :current-speakers="currentSpeakers"
      :recording-id="recordingId"
      :selected-segment="selectedSegment"
      @speaker-updated="handleSpeakerUpdated"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import { Loading, DocumentCopy, Reading, ChatDotRound, CircleClose } from '@element-plus/icons-vue'
import recordingService from '@/services/recordingService'
import http from '@/services/http'
import type { RecordingDetail, SpeechSegment, IntelligentSummary, Keyword } from '@/services/recordingService'
import AudioPlayer from '@/components/AudioPlayer.vue'
import SpeakerSettingDialog from '@/components/SpeakerSettingDialog.vue'
import { useSpeakerStore, type Speaker } from '@/stores/speakerStore'

const route = useRoute()
const router = useRouter()

// 使用speakerStore
const speakerStore = useSpeakerStore()

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

// AI处理状态
const aiProcessing = ref(false)
const summaryLoading = ref(false)
const keywordsLoading = ref(false)
const chaptersLoading = ref(false)
const transcriptLoading = ref(false)
const processingTimer = ref<number | null>(null)

// 轮询控制参数
const pollingAttempts = ref(0)
const maxPollingAttempts = ref(40) // 最大轮询次数 (40次 * 3秒 = 2分钟)
const consecutiveFailures = ref(0)
const maxConsecutiveFailures = ref(5) // 最大连续失败次数
const pollingStartTime = ref(0)
const maxPollingDuration = ref(5 * 60 * 1000) // 最大轮询时长：5分钟

// 发言人设置相关状态
const showSpeakerSetting = ref(false)
const selectedSegment = ref<{
  id: string
  speakerName: string
  speakerNumber: string
  speakerColor: string
  speakerId: string
} | undefined>(undefined)

// 当前录音的发言人列表
const currentSpeakers = ref<Array<{
  id: string
  name: string
  color: string
  number?: string
  segmentCount?: number
}>>([])

// 使用store的常用发言人方法

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

// 音频播放器专用的段落数据（转换格式以适配AudioPlayer组件）
const audioSegments = computed(() => {
  return segments.value.map((segment, index) => ({
    id: segment.id || index + 1,
    speakerName: segment.speakerName,
    speakerNumber: segment.speakerNumber ? parseInt(segment.speakerNumber) : 1,
    speakerColor: segment.speakerColor,
    startTime: segment.startTime,
    endTime: segment.endTime,
    text: segment.content || segment.text
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
  // 设置播放时间，AudioPlayer组件会监听currentPlayTime的变化
  currentPlayTime.value = segment.startTime
}

const jumpToChapter = (startTime: number) => {
  currentPlayTime.value = startTime
  // 音频播放器会通过watch监听currentPlayTime的变化
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

// 发言人设置相关方法
const openSpeakerSetting = (segment: any) => {
  selectedSegment.value = {
    id: segment.id,
    speakerName: segment.speakerName,
    speakerNumber: segment.speakerNumber,
    speakerColor: segment.speakerColor,
    speakerId: segment.speakerId || segment.speakerNumber || 'speaker1'
  }
  showSpeakerSetting.value = true
}

// 发言人更新成功后的处理
const handleSpeakerUpdated = async () => {
  try {
    // 重新加载录音详情以获取最新的发言人信息
    await loadRecordingDetail()
    ElMessage.success('发言人信息已更新')
  } catch (error) {
    console.error('重新加载数据失败:', error)
    ElMessage.error('更新成功，但刷新数据失败，请手动刷新页面')
  }
}

// 生成当前录音的发言人列表
const generateCurrentSpeakers = () => {
  const speakerMap = new Map<string, any>()
  
  segments.value.forEach(segment => {
    const speakerNumber = segment.speakerNumber
    if (!speakerMap.has(speakerNumber)) {
      speakerMap.set(speakerNumber, {
        id: `current-${speakerNumber}`,
        name: segment.speakerName,
        color: segment.speakerColor,
        number: speakerNumber,
        segmentCount: 0
      })
    }
    
    const speaker = speakerMap.get(speakerNumber)!
    speaker.segmentCount = (speaker.segmentCount || 0) + 1
  })
  
  currentSpeakers.value = Array.from(speakerMap.values())
}

// 获取发言人头像显示文本
const getSpeakerAvatarText = (segment: any) => {
  const name = segment.speakerName || ''
  
  // 检查是否是默认格式的姓名（如"发言人1"、"发言人2"等）
  const isDefaultName = /^发言人\s*\d+$/.test(name.trim())
  
  // 如果是默认姓名或者姓名为空，显示数字
  if (!name.trim() || isDefaultName) {
    return segment.speakerNumber || '1'
  }
  
  // 否则显示姓名的第一个字符
  return name.charAt(0)
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
        audioUrl: `${http.defaults.baseURL}/api/recordings/${recording.id}/download`,
        status: recording.status
      }
      
      console.log('音频URL:', recordingDetail.value.audioUrl)
      
      // 转换段落数据格式（后端已返回驼峰格式，直接使用）
      if (rawSegments && rawSegments.length > 0) {
        segments.value = rawSegments.map((segment: any, index) => ({
          ...segment,
          text: segment.content, // 添加text字段以兼容模板
          speakerNumber: (segment.speakerId || '').replace(/[^0-9]/g, '') || String(index + 1), // 提取数字作为发言人编号
          highlightedText: ''
        }))
        transcriptLoading.value = false
        
        // 生成当前录音的发言人列表
        generateCurrentSpeakers()
      } else {
        transcriptLoading.value = true
      }
      
      // 检查AI处理状态
      checkAIProcessingStatus(recording.status, rawSummary, rawKeywords)
      
      // 设置摘要数据（后端已返回驼峰格式，直接使用）
      if (rawSummary) {
        summary.value = rawSummary
        summaryLoading.value = false
      }
      
      // 设置关键词数据
      if (rawKeywords && rawKeywords.length > 0) {
        keywords.value = rawKeywords
        keywordsLoading.value = false
      }
      
      // 生成章节数据（基于发言人变化和时间间隔）
      if (segments.value.length > 0) {
        generateChapters()
        chaptersLoading.value = false
      }
      
      console.log('录音详情加载完成:', recording.title)
    } else {
      throw new Error('获取录音详情失败')
    }
  } catch (error: any) {
    console.error('加载录音详情失败:', error)
    
    // 开发模式下，提供演示数据
    if (import.meta.env.DEV) {
      console.log('开发模式：使用演示数据')
      loadDemoData()
    } else {
      if (error.response?.status === 404) {
        ElMessage.error('录音记录不存在')
        router.push('/recordings')
      } else if (error.response?.status === 500) {
        ElMessage.error('服务器错误，请稍后重试')
      } else {
        ElMessage.error(`加载失败: ${error.message || '未知错误'}`)
      }
    }
  } finally {
    loading.value = false
  }
}

// 加载演示数据（用于开发和测试）
const loadDemoData = () => {
  console.log('加载演示数据...')
  
  recordingDetail.value = {
    id: recordingId,
    title: '演示录音 - 项目讨论会议',
    duration: 120, // 2分钟
    language: '中文',
    createTime: '2025-01-01 16:30',
    speakerCount: 2,
    audioUrl: 'https://www.soundjay.com/misc/sounds/bell-ringing-05.wav', // 示例音频
    status: 'completed'
  }
  
  segments.value = [
    {
      id: 1,
      speakerId: 'SPEAKER_00',
      speakerName: '发言人1',
      speakerNumber: '1',
      speakerColor: '#1890ff',
      content: '大家好，今天我们来讨论一下项目的进展情况。',
      text: '大家好，今天我们来讨论一下项目的进展情况。',
      startTime: 0,
      endTime: 5,
      confidence: 0.95,
      highlightedText: ''
    },
    {
      id: 2,
      speakerId: 'SPEAKER_01',
      speakerName: '发言人2',
      speakerNumber: '2',
      speakerColor: '#52c41a',
      content: '好的，我来汇报一下技术方面的进展。目前前端开发已经完成了80%。',
      text: '好的，我来汇报一下技术方面的进展。目前前端开发已经完成了80%。',
      startTime: 6,
      endTime: 12,
      confidence: 0.92,
      highlightedText: ''
    },
    {
      id: 3,
      speakerId: 'SPEAKER_00',
      speakerName: '发言人1',
      speakerNumber: '1',
      speakerColor: '#1890ff',
      content: '很好，那后端的API接口开发情况如何？',
      text: '很好，那后端的API接口开发情况如何？',
      startTime: 13,
      endTime: 18,
      confidence: 0.90,
      highlightedText: ''
    },
    {
      id: 4,
      speakerId: 'SPEAKER_01',
      speakerName: '发言人2',
      speakerNumber: '2',
      speakerColor: '#52c41a',
      content: '后端接口基本完成，正在进行联调测试。预计本周内可以完成所有功能。',
      text: '后端接口基本完成，正在进行联调测试。预计本周内可以完成所有功能。',
      startTime: 19,
      endTime: 26,
      confidence: 0.93,
      highlightedText: ''
    }
  ]
  
  summary.value = {
    content: '本次会议主要讨论了项目开发进展。前端开发已完成80%，后端API开发基本完成，正在进行联调测试，预计本周内完成所有功能开发。',
    quality: 4,
    wordCount: 156,
    keyPoints: ['前端开发进展', '后端API接口', '联调测试', '完成时间'],
    summaryType: 'meeting'
  }
  
  keywords.value = [
    { word: '项目', count: 5, score: 0.9, source: 'ai' },
    { word: '开发', count: 4, score: 0.8, source: 'ai' },
    { word: '前端', count: 3, score: 0.7, source: 'ai' },
    { word: '后端', count: 3, score: 0.7, source: 'ai' },
    { word: '接口', count: 2, score: 0.6, source: 'ai' },
    { word: '测试', count: 2, score: 0.5, source: 'ai' }
  ]
  
  generateChapters()
  generateCurrentSpeakers()
  transcriptLoading.value = false
  ElMessage.success('演示数据加载完成')
}

// 检查AI处理状态
const checkAIProcessingStatus = (status: string, summaryData: any, keywordsData: any) => {
  // 如果录音状态是处理中，或者缺少AI生成的内容
  const needsProcessing = status === 'processing' || !summaryData || !keywordsData || keywordsData.length === 0
  
  if (needsProcessing) {
    aiProcessing.value = true
    summaryLoading.value = !summaryData
    keywordsLoading.value = !keywordsData || keywordsData.length === 0
    chaptersLoading.value = segments.value.length === 0
    transcriptLoading.value = segments.value.length === 0
    
    // 重置轮询计数器
    pollingAttempts.value = 0
    consecutiveFailures.value = 0
    pollingStartTime.value = Date.now()
    
    // 开始轮询检查处理状态
    startProcessingPolling()
    console.log('AI正在处理中，启动状态轮询')
  } else {
    aiProcessing.value = false
    summaryLoading.value = false
    keywordsLoading.value = false
    chaptersLoading.value = false
    transcriptLoading.value = false
    stopProcessingPolling()
    console.log('AI处理已完成')
  }
}

// 开始轮询检查处理状态
const startProcessingPolling = () => {
  // 清除之前的定时器
  stopProcessingPolling()
  
  // 每3秒检查一次状态
  processingTimer.value = window.setInterval(async () => {
    try {
      pollingAttempts.value++
      
      // 检查是否超过最大轮询次数
      if (pollingAttempts.value > maxPollingAttempts.value) {
        console.warn('达到最大轮询次数，停止轮询')
        stopProcessingPolling()
        ElMessage.warning('AI处理时间较长，请稍后手动刷新页面查看结果')
        return
      }
      
      // 检查是否超过最大轮询时长
      const elapsedTime = Date.now() - pollingStartTime.value
      if (elapsedTime > maxPollingDuration.value) {
        console.warn('达到最大轮询时长，停止轮询')
        stopProcessingPolling()
        ElMessage.warning('AI处理超时，请稍后手动刷新页面查看结果')
        return
      }
      
      // 检查是否连续失败次数过多
      if (consecutiveFailures.value >= maxConsecutiveFailures.value) {
        console.warn('连续失败次数过多，停止轮询')
        stopProcessingPolling()
        ElMessage.error('网络连接异常，请检查网络后手动刷新页面')
        return
      }
      
      console.log(`检查AI处理状态... (第${pollingAttempts.value}次，已运行${Math.round(elapsedTime/1000)}秒)`)
      const response = await recordingService.getRecordingDetail(recordingId)
      
      if (response.success && response.data) {
        // 重置连续失败计数
        consecutiveFailures.value = 0
        
        const { recording, segments: rawSegments, summary: rawSummary, keywords: rawKeywords } = response.data
        
        // 检查转写内容是否已生成
        if (transcriptLoading.value && rawSegments && rawSegments.length > 0) {
          segments.value = rawSegments.map((segment: any, index) => ({
            ...segment,
            text: segment.content,
            speakerNumber: (segment.speakerId || '').replace(/[^0-9]/g, '') || String(index + 1),
            highlightedText: ''
          }))
          transcriptLoading.value = false
          generateCurrentSpeakers()
          ElMessage.success('转写内容加载完成')
        }
        
        // 检查摘要是否已生成
        if (summaryLoading.value && rawSummary) {
          summary.value = rawSummary
          summaryLoading.value = false
          ElMessage.success('智能摘要生成完成')
        }
        
        // 检查关键词是否已生成
        if (keywordsLoading.value && rawKeywords && rawKeywords.length > 0) {
          keywords.value = rawKeywords
          keywordsLoading.value = false
          ElMessage.success('关键词提取完成')
        }
        
        // 检查章节是否需要重新生成
        if (chaptersLoading.value && segments.value.length > 0) {
          generateChapters()
          chaptersLoading.value = false
        }
        
        // 如果所有AI处理都完成了，停止轮询
        if (!transcriptLoading.value && !summaryLoading.value && !keywordsLoading.value && !chaptersLoading.value) {
          aiProcessing.value = false
          stopProcessingPolling()
          ElMessage.success('AI分析完成')
          console.log('AI处理全部完成，停止轮询')
        }
      } else {
        // API返回失败，但不立即停止轮询
        consecutiveFailures.value++
        console.warn(`API请求失败 (连续失败${consecutiveFailures.value}次):`, response)
      }
    } catch (error) {
      consecutiveFailures.value++
      console.error(`检查处理状态失败 (连续失败${consecutiveFailures.value}次):`, error)
      
      // 如果连续失败次数还没达到上限，继续重试
      if (consecutiveFailures.value < maxConsecutiveFailures.value) {
        console.log('继续重试轮询...')
      }
    }
  }, 3000) // 每3秒检查一次
  
  console.log('开始AI处理状态轮询，最大轮询次数:', maxPollingAttempts.value, '最大时长:', maxPollingDuration.value / 1000, '秒')
}

// 停止轮询
const stopProcessingPolling = () => {
  if (processingTimer.value) {
    clearInterval(processingTimer.value)
    processingTimer.value = null
    console.log('已停止AI处理状态轮询')
  }
}

// 手动停止轮询（用户操作）
const manualStopPolling = () => {
  stopProcessingPolling()
  aiProcessing.value = false
  summaryLoading.value = false
  keywordsLoading.value = false
  chaptersLoading.value = false
  transcriptLoading.value = false
  ElMessage.info('已停止AI处理状态检查')
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
  // 清理AI处理状态轮询定时器
  stopProcessingPolling()
  console.log('页面卸载，清理资源')
})
</script>

<style scoped>
.recording-detail-view {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background-color: #f5f7fa;
  padding-bottom: 120px; /* 为底部播放器留出空间 */
}

.detail-header {
  position: sticky;
  top: 0;
  z-index: 10;
  background-color: #fff;
  padding: 16px 20px;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.recording-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.meta-info {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
  color: #909399;
  font-size: 14px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.detail-content {
  flex: 1;
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

.section {
  margin-bottom: 15px;
  background: #fff;
  border-radius: 8px;
}

.section-header {
  padding: 16px 20px;
  border-bottom: 1px solid #f0f2f5;
}

.section-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.section-content {
  padding: 15px 20px;
}

/* 关键词区域样式 */
.keywords-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  padding: 8px 0;
}

.keyword-tag {
  cursor: pointer;
  transition: all 0.3s;
}

.keyword-tag:hover {
  transform: translateY(-2px);
}

/* 摘要区域样式 */
.summary-wrapper {
  line-height: 1.8;
  color: #303133;
}

.summary-text {
  font-size: 15px;
  white-space: pre-wrap;
}

.summary-meta {
  margin-top: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 章节区域样式 */
.chapters-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.chapter-item {
  padding: 16px;
  border-radius: 8px;
  background: #f9fafc;
  cursor: pointer;
  transition: all 0.3s;
}

.chapter-item:hover {
  background: #f0f2f5;
}

.chapter-time {
  color: #909399;
  font-size: 14px;
  margin-bottom: 8px;
}

.chapter-title {
  font-weight: 500;
  color: #303133;
  margin-bottom: 8px;
}

.chapter-summary {
  color: #606266;
  font-size: 14px;
  line-height: 1.6;
}

/* 转写原文区域样式 */
.transcript-content {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.transcript-segment {
  padding: 16px;
  border-radius: 8px;
  background: #f9fafc;
  transition: all 0.3s;
}

.transcript-segment:hover {
  background: #f0f2f5;
}

.transcript-segment.playing {
  background: #ecf5ff;
}

.transcript-segment.highlighted {
  background: #fdf6ec;
}

.segment-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.speaker-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.speaker-avatar {
  cursor: pointer;
}

.speaker-name {
  font-weight: 500;
  color: #303133;
  cursor: pointer;
}

.segment-time {
  color: #909399;
  font-size: 14px;
}

.segment-content {
  color: #303133;
  line-height: 1.8;
  font-size: 15px;
}

/* Loading状态样式 */
.loading-text {
  text-align: center;
  margin-top: 12px;
  color: #409eff;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

/* 音频播放器样式 */
.audio-player-section {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: #fff;
  box-shadow: 0 -2px 8px rgba(0, 0, 0, 0.1);
  z-index: 100;
}

/* 处理状态指示器样式 */
.processing-indicator {
  position: fixed;
  bottom: 120px;
  right: 24px;
  background: #fff;
  padding: 12px 16px;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  z-index: 99;
  max-width: 400px;
}

.processing-content {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.processing-text {
  flex: 1;
  font-size: 14px;
  color: #606266;
}

/* 空状态样式 */
.empty-placeholder {
  text-align: center;
  padding: 48px 0;
  color: #909399;
}

.empty-placeholder .el-icon {
  margin-bottom: 16px;
}

.empty-state {
  padding: 32px 0;
}

/* 响应式调整 */
@media screen and (max-width: 768px) {
  .detail-header {
    padding: 12px 16px;
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
  }

  .header-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .detail-content {
    padding: 16px;
  }

  .section-header {
    padding: 12px 16px;
  }

  .section-content {
    padding: 16px;
  }
}
</style>
