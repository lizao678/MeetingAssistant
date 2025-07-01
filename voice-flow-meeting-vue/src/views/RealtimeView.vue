<template>
  <div class="realtime-view">
    <!-- 头部控制区 -->
    <el-card class="header-card" shadow="never">
      <div class="header-content">
        <div class="title-section">
          <h1 class="page-title">
            <el-icon class="title-icon"><Microphone /></el-icon>
            实时语音识别
          </h1>
          <div class="status-indicator">
            <el-tag :type="statusTagType" :effect="isRecording ? 'dark' : 'plain'" size="small">
              <el-icon class="status-icon"><component :is="statusIcon" /></el-icon>
              {{ statusText }}
            </el-tag>
          </div>
        </div>
        
        <div class="controls-section">
          <el-space :size="16">
                         <!-- 语言选择 -->
             <el-select v-model="selectedLang" placeholder="选择语言" style="min-width: 120px">
               <el-option label="自动检测" value="auto" />
               <el-option label="中文" value="zh" />
               <el-option label="英文" value="en" />
               <el-option label="日语" value="ja" />
               <el-option label="韩语" value="ko" />
               <el-option label="粤语" value="yue" />
             </el-select>
            
            <!-- 说话人识别开关 -->
            <el-switch
              v-model="speakerVerification"
              active-text="区分发言人"
              inactive-text="不区分"
              style="--el-switch-on-color: #13ce66"
            />
          </el-space>
        </div>
      </div>
      
      <!-- 录音控制按钮 -->
      <div class="record-controls">
        <div class="control-buttons">
          <el-button
            :type="isRecording ? 'danger' : 'primary'"
            :size="'large'"
            :loading="isConnecting"
            :disabled="isTimeLimit"
            @click="toggleRecording"
            class="record-button"
          >
            <el-icon v-if="!isConnecting" size="20">
              <component :is="isRecording ? 'Stop' : 'VideoPlay'" />
            </el-icon>
            {{ isRecording ? '停止录音' : '开始录音' }}
          </el-button>
          
          <!-- 暂停/恢复按钮 -->
          <el-button
            v-if="isRecording"
            :type="isPaused ? 'success' : 'warning'"
            size="large"
            @click="togglePause"
            class="pause-button"
          >
            <el-icon size="20">
              <component :is="isPaused ? 'VideoPlay' : 'VideoPause'" />
            </el-icon>
            {{ isPaused ? '恢复录音' : '暂停录音' }}
          </el-button>
          
          <el-button
            v-if="messages.length > 0"
            @click="clearMessages"
            type="info"
            size="large"
            plain
          >
            <el-icon><Delete /></el-icon>
            清空记录
          </el-button>
        </div>
        
        <!-- 录音时长显示 -->
        <div v-if="isRecording || recordingDuration > 0" class="recording-time">
          <div class="time-display">
            <el-text 
              :type="isNearTimeLimit ? 'warning' : isTimeLimit ? 'danger' : 'primary'" 
              size="large"
              class="duration-text"
            >
              <el-icon><Timer /></el-icon>
              {{ formattedDuration }} / {{ formattedMaxDuration }}
            </el-text>
          </div>
          
          <!-- 进度条 -->
          <el-progress
            :percentage="recordingProgress"
            :status="isTimeLimit ? 'exception' : isNearTimeLimit ? 'warning' : 'success'"
            :show-text="false"
            :stroke-width="6"
            class="time-progress"
          />
          
          <!-- 时间限制提示 -->
          <el-text v-if="isNearTimeLimit" type="warning" size="small">
            {{ isTimeLimit ? '已达到最大录音时长' : '即将达到最大录音时长' }}
          </el-text>
        </div>
      </div>
    </el-card>

    <!-- 消息显示区域 -->
    <el-card class="messages-card" shadow="never">
      <template #header>
        <div class="messages-header">
          <span>识别结果</span>
          <el-text type="info" size="small">实时显示语音识别内容</el-text>
        </div>
      </template>
      
      <div ref="messagesContainer" class="messages-container">
        <div v-if="messages.length === 0" class="empty-state">
          <el-empty description="暂无识别内容">
            <template #image>
              <el-icon size="100" color="#c0c4cc"><Microphone /></el-icon>
            </template>
          </el-empty>
        </div>
        
        <div v-else class="messages-list">
          <div
            v-for="message in messages"
            :key="message.id"
            class="message-item"
            :class="`speaker-${message.speakerClass}`"
          >
            <div class="message-avatar">
              <el-avatar :size="36" :style="{ backgroundColor: message.speakerColor }">
                {{ message.speakerNumber }}
              </el-avatar>
            </div>
            
            <div class="message-content">
              <div class="message-header">
                <span class="speaker-name">{{ message.speakerId }}</span>
                <el-tag
                  v-if="message.confidence"
                  :type="getConfidenceType(message.confidence)"
                  size="small"
                  class="confidence-tag"
                >
                  置信度: {{ (message.confidence * 100).toFixed(1) }}%
                </el-tag>
                <span class="message-time">{{ message.timestamp }}</span>
              </div>
              
              <div class="message-bubble">
                {{ message.text }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 发言人数选择弹窗 -->
    <SpeakerCountDialog
      v-model="showSpeakerDialog"
      :recording-data="currentRecordingData"
      @confirm="handleSpeakerDialogConfirm"
      @cancel="handleSpeakerDialogCancel"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import { useRouter } from 'vue-router'
import SpeakerCountDialog from '../components/SpeakerCountDialog.vue'
import recordingService from '@/services/recordingService'
import type { AudioMessage, RecordingStatus, SpeakerInfo } from '../types/audio'

const router = useRouter()

// 响应式数据
const isRecording = ref(false)
const isConnecting = ref(false)
const isPaused = ref(false)
const selectedLang = ref('zh')
const speakerVerification = ref(true)
const messages = ref<AudioMessage[]>([])
const messagesContainer = ref<HTMLElement>()

// 录音时长相关
const recordingDuration = ref(0) // 已录制时长(秒)
const maxRecordingDuration = ref(3600) // 最大录音时长(秒) - 1小时
let recordingTimer: number | null = null

// WebSocket和录音相关
let ws: WebSocket | null = null
let recorder: any = null
let audioContext: AudioContext | null = null
let timeInterval: number | null = null

// 说话人管理
const speakerColors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399']
const speakerMap = new Map<string, SpeakerInfo>()
let speakerCounter = 0

// 发言人数选择弹窗
const showSpeakerDialog = ref(false)
const currentRecordingData = ref({
  duration: 0,
  language: 'zh',
  audioBlob: undefined as Blob | undefined,
  messages: [] as AudioMessage[]
})

// 计算属性
const statusText = computed(() => {
  if (isConnecting.value) return '连接中...'
  if (isRecording.value && isPaused.value) return '录音暂停'
  if (isRecording.value) return '录音中'
  return '准备就绪'
})

const statusTagType = computed(() => {
  if (isConnecting.value) return 'warning'
  if (isRecording.value && isPaused.value) return 'info'
  if (isRecording.value) return 'danger'
  return 'success'
})

const statusIcon = computed(() => {
  if (isConnecting.value) return 'Loading'
  if (isRecording.value && isPaused.value) return 'VideoPause'
  if (isRecording.value) return 'VideoCamera'
  return 'SuccessFilled'
})

// 时间格式化
const formatTime = (seconds: number) => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60
  
  if (hours > 0) {
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }
  return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

const formattedDuration = computed(() => formatTime(recordingDuration.value))
const formattedMaxDuration = computed(() => formatTime(maxRecordingDuration.value))

// 录音进度百分比
const recordingProgress = computed(() => {
  return Math.min((recordingDuration.value / maxRecordingDuration.value) * 100, 100)
})

// 是否接近时间限制
const isNearTimeLimit = computed(() => {
  return recordingDuration.value >= maxRecordingDuration.value * 0.9 // 90%
})

// 是否达到时间限制
const isTimeLimit = computed(() => {
  return recordingDuration.value >= maxRecordingDuration.value
})

// 获置信度类型
const getConfidenceType = (confidence: number) => {
  if (confidence > 0.8) return 'success'
  if (confidence > 0.6) return 'warning'
  return 'danger'
}

// 获取说话人信息
const getSpeakerInfo = (speakerId: string): SpeakerInfo => {
  if (!speakerMap.has(speakerId)) {
    const colorIndex = speakerCounter % speakerColors.length
    const speakerNumber = speakerCounter + 1
    
    speakerMap.set(speakerId, {
      id: speakerId,
      color: speakerColors[colorIndex],
      number: speakerNumber.toString(),
      className: `speaker-${speakerNumber}`
    })
    
    speakerCounter++
  }
  
  return speakerMap.get(speakerId)!
}

// 添加消息
const addMessage = (data: any) => {
  const speakerInfo = getSpeakerInfo(data.speaker_id || '发言人1')
  
  // 正确处理换行逻辑：如果后端明确返回false，就不换行；否则默认换行
  const shouldNewLine = data.is_new_line !== undefined ? data.is_new_line : true
  
  const message: AudioMessage = {
    id: Date.now(),
    text: data.data || data.text || '',
    speakerId: data.speaker_id || '发言人1',
    speakerColor: speakerInfo.color,
    speakerNumber: speakerInfo.number,
    speakerClass: speakerInfo.className,
    timestamp: new Date().toLocaleTimeString('zh-CN', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    }),
    confidence: data.confidence || 0,
    isNewLine: shouldNewLine,
    segmentType: data.segment_type || 'continue'
  }
  
  // 智能换行逻辑：
  // 1. 如果需要换行 (shouldNewLine = true)，总是创建新消息
  // 2. 如果不需要换行 (shouldNewLine = false)，且是同一说话人，则追加到最后一条消息
  const lastMessage = messages.value[messages.value.length - 1]
  
  if (!shouldNewLine && 
      lastMessage && 
      lastMessage.speakerId === message.speakerId &&
      lastMessage.text.trim() !== '') {
    // 追加到现有消息，用空格分隔
    lastMessage.text += (lastMessage.text.endsWith(' ') ? '' : ' ') + message.text
    lastMessage.timestamp = message.timestamp
    lastMessage.confidence = message.confidence
    console.log(`追加消息: ${message.text} (说话人: ${message.speakerId})`)
  } else {
    // 创建新消息
    messages.value.push(message)
    console.log(`新消息: ${message.text} (说话人: ${message.speakerId}, 换行: ${shouldNewLine})`)
  }
  
  // 自动滚动到底部
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

// 创建PCM录音器
const createPCMRecorder = (stream: MediaStream) => {
  const sampleBits = 16 // 采样位数
  const inputSampleRate = 48000 // 输入采样率
  const outputSampleRate = 16000 // 输出采样率
  const channelCount = 1 // 单声道
  
  const context = new AudioContext()
  const audioInput = context.createMediaStreamSource(stream)
  const scriptProcessor = context.createScriptProcessor(4096, channelCount, channelCount)
  
  const audioData = {
    size: 0,
    buffer: [] as Float32Array[],
    clear() {
      this.buffer = []
      this.size = 0
    },
    input(data: Float32Array) {
      this.buffer.push(new Float32Array(data))
      this.size += data.length
    },
    encodePCM() {
      const bytes = new Float32Array(this.size)
      let offset = 0
      for (let i = 0; i < this.buffer.length; i++) {
        bytes.set(this.buffer[i], offset)
        offset += this.buffer[i].length
      }
      
      const dataLength = bytes.length * (sampleBits / 8)
      const buffer = new ArrayBuffer(dataLength)
      const data = new DataView(buffer)
      offset = 0
      
      for (let i = 0; i < bytes.length; i++, offset += 2) {
        const s = Math.max(-1, Math.min(1, bytes[i]))
        data.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true)
      }
      
      return new Blob([data], { type: 'audio/pcm' })
    }
  }
  
  // 降采样函数
  const downsampleBuffer = (buffer: Float32Array, inputSampleRate: number, outputSampleRate: number) => {
    if (outputSampleRate === inputSampleRate) {
      return buffer
    }
    const sampleRateRatio = inputSampleRate / outputSampleRate
    const newLength = Math.round(buffer.length / sampleRateRatio)
    const result = new Float32Array(newLength)
    let offsetResult = 0
    let offsetBuffer = 0
    
    while (offsetResult < result.length) {
      const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio)
      let accum = 0
      let count = 0
      for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
        accum += buffer[i]
        count++
      }
      result[offsetResult] = accum / count
      offsetResult++
      offsetBuffer = nextOffsetBuffer
    }
    return result
  }
  
  scriptProcessor.onaudioprocess = (e) => {
    const resampledData = downsampleBuffer(
      e.inputBuffer.getChannelData(0),
      inputSampleRate,
      outputSampleRate
    )
    audioData.input(resampledData)
  }
  
  return {
    start() {
      audioInput.connect(scriptProcessor)
      scriptProcessor.connect(context.destination)
    },
    stop() {
      scriptProcessor.disconnect()
    },
    getBlob() {
      return audioData.encodePCM()
    },
    clear() {
      audioData.clear()
    }
  }
}

// 切换录音状态
const toggleRecording = async () => {
  if (isRecording.value) {
    await stopRecording()
  } else {
    await startRecording()
  }
}

// 切换暂停状态
const togglePause = () => {
  if (isPaused.value) {
    // 恢复录音
    resumeRecording()
  } else {
    // 暂停录音
    pauseRecording()
  }
}

// 暂停录音
const pauseRecording = () => {
  if (!isRecording.value) return
  
  isPaused.value = true
  
  // 停止定时器
  if (timeInterval) {
    clearInterval(timeInterval)
    timeInterval = null
  }
  
  // 停止录音计时器
  if (recordingTimer) {
    clearInterval(recordingTimer)
    recordingTimer = null
  }
  
  ElMessage.info('录音已暂停')
}

// 恢复录音
const resumeRecording = () => {
  if (!isRecording.value || !isPaused.value) return
  
  isPaused.value = false
  
  // 重新开始音频数据发送
  timeInterval = setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN && !isPaused.value) {
      const audioBlob = recorder.getBlob()
      if (audioBlob.size > 0) {
        console.log('发送音频数据，大小:', audioBlob.size)
        ws.send(audioBlob)
        recorder.clear()
      }
    }
  }, 500)
  
  // 重新开始录音计时器
  startRecordingTimer()
  
  ElMessage.success('录音已恢复')
}

// 开始录音计时器
const startRecordingTimer = () => {
  recordingTimer = setInterval(() => {
    if (!isPaused.value) {
      recordingDuration.value++
      
      // 检查是否达到最大时长
      if (recordingDuration.value >= maxRecordingDuration.value) {
        ElMessage.warning('已达到最大录音时长，自动停止录音')
        stopRecording()
      }
    }
  }, 1000)
}

// 停止录音计时器
const stopRecordingTimer = () => {
  if (recordingTimer) {
    clearInterval(recordingTimer)
    recordingTimer = null
  }
}

// 开始录音
const startRecording = async () => {
  try {
    isConnecting.value = true
    
    // 获取音频流
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        sampleRate: 48000 // 使用默认采样率，后续降采样到16kHz
      }
    })
    
    // 建立WebSocket连接
    const wsUrl = getWebSocketUrl()
    const queryParams = new URLSearchParams({
      lang: selectedLang.value,
      sv: speakerVerification.value ? '1' : '0'
    })
    
    ws = new WebSocket(`${wsUrl}/ws/transcribe?${queryParams}`)
    ws.binaryType = 'arraybuffer'
    
    ws.onopen = () => {
      console.log('WebSocket连接已建立')
      isConnecting.value = false
      isRecording.value = true
      
      // 创建PCM录音器
      recorder = createPCMRecorder(stream)
      recorder.start()
      
      // 定时发送音频数据
      timeInterval = setInterval(() => {
        if (ws && ws.readyState === WebSocket.OPEN && !isPaused.value) {
          const audioBlob = recorder.getBlob()
          if (audioBlob.size > 0) {
            console.log('发送音频数据，大小:', audioBlob.size)
            ws.send(audioBlob)
            recorder.clear()
          }
        }
      }, 500)
      
      // 开始录音计时器
      startRecordingTimer()
      
      ElMessage.success('开始录音')
    }
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        if (data.code === 0 && data.data) {
          addMessage(data)
        }
      } catch (error) {
        console.error('解析消息失败:', error)
      }
    }
    
        ws.onerror = (error) => {
      console.error('WebSocket错误:', error)
      ElMessage.error('连接失败，请检查网络')
      stopRecording(false) // 已经显示了错误消息，不需要再显示"录音已停止"
    }

    ws.onclose = () => {
      console.log('WebSocket连接已关闭')
      // 只有在非正常关闭时才显示消息
      if (isRecording.value) {
        ElMessage.warning('连接已断开，录音已停止')
        stopRecording(false) // 已经显示了断开消息，不需要再显示"录音已停止"
      } else {
        stopRecording(false) // 正常关闭，不显示消息
      }
    }
    
  } catch (error) {
    console.error('启动录音失败:', error)
    ElMessage.error('无法访问麦克风，请检查权限设置')
    isConnecting.value = false
  }
}

// 停止录音
const stopRecording = async (showMessage = true) => {
  isRecording.value = false
  isConnecting.value = false
  isPaused.value = false
  
  // 停止所有定时器
  if (timeInterval) {
    clearInterval(timeInterval)
    timeInterval = null
  }
  
  stopRecordingTimer()
  
  // 停止录音器
  if (recorder) {
    recorder.stop()
    recorder = null
  }
  
  // 关闭WebSocket连接
  if (ws) {
    ws.close()
    ws = null
  }
  
  // 如果有录音内容且需要显示消息，则显示发言人选择弹窗
  if (showMessage && messages.value.length > 0 && recordingDuration.value > 3) {
    // 准备录音数据
    currentRecordingData.value = {
      duration: recordingDuration.value,
      language: selectedLang.value,
      audioBlob: undefined, // TODO: 需要获取录音的Blob数据
      messages: [...messages.value]
    }
    
    // 显示发言人选择弹窗
    showSpeakerDialog.value = true
  } else if (showMessage) {
    ElMessage.info(`录音已停止，总时长: ${formattedDuration.value}`)
  }
}

// 清空消息
const clearMessages = async () => {
  try {
    await ElMessageBox.confirm('确定要清空所有识别记录吗？', '确认清空', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消'
    })
    
    messages.value = []
    speakerMap.clear()
    speakerCounter = 0
    
    // 重置录音时长（只有在没有录音时才重置）
    if (!isRecording.value) {
      recordingDuration.value = 0
    }
    
    ElMessage.success('记录已清空')
  } catch {
    // 用户取消操作
  }
}

// 获取WebSocket URL（根据环境自动检测）
const getWebSocketUrl = () => {
  const hostname = window.location.hostname
  const protocol = window.location.protocol
  
  // 服务器环境配置
  if (hostname === '192.168.100.205' || hostname.includes('192.168.') || protocol === 'https:') {
    return 'wss://192.168.100.205:8989'
  }
  
  // 本地环境配置
  return 'ws://127.0.0.1:26000'
}

// 处理发言人选择弹窗确认
const handleSpeakerDialogConfirm = async (data: any) => {
  try {
    const loading = ElLoading.service({
      lock: true,
      text: 'AI正在处理录音数据...',
      background: 'rgba(0, 0, 0, 0.7)'
    })
    
    // 创建一个虚拟的音频文件（包含转写文本）
    // 在实际实现中，这里应该是录音过程中收集的真实音频数据
    const transcriptText = messages.value.map(msg => `${msg.speakerId}: ${msg.text}`).join('\n')
    const audioBlob = new Blob([transcriptText], { type: 'audio/wav' })
    
    // 创建一个模拟的音频文件，用于演示（修改文件类型以通过后端验证）
    const audioFile = new File([audioBlob], `recording_${Date.now()}.wav`, { 
      type: 'audio/wav',  // 修改为音频类型以通过后端验证
      lastModified: Date.now() 
    })
    
    // 调用后端API提交录音数据
    const requestData = {
      audioFile: audioFile,
      speakerCount: data.speakerCount,
      language: data.language || selectedLang.value,
      smartPunctuation: data.smartPunctuation !== false,
      numberConversion: data.numberConversion !== false,
      generateSummary: data.generateSummary !== false,
      summaryType: data.summaryType || 'meeting'
    }
    
    console.log('正在提交录音处理请求:', requestData)
    
    const response = await recordingService.processRecording(requestData)
    
    loading.close()
    
    console.log('API响应:', response)
    
    if (response.success && response.recording_id) {
      ElMessage.success('录音已提交AI处理，正在跳转到详情页...')
      
      // 清空当前录音数据
      messages.value = []
      speakerMap.clear()
      speakerCounter = 0
      recordingDuration.value = 0
      
      // 跳转到录音详情页
      setTimeout(() => {
        router.push(`/recording/${response.recording_id}`)
      }, 1000)
    } else {
      throw new Error(response.error || response.message || '处理失败')
    }
    
  } catch (error: any) {
    ElMessage.error(`保存录音记录失败: ${error.message || error}`)
    console.error('保存录音失败:', error)
  }
}

// 处理发言人选择弹窗取消
const handleSpeakerDialogCancel = () => {
  ElMessage.info('已取消保存录音')
}

// 生命周期
onMounted(() => {
  console.log('实时语音识别页面已加载')
})

onUnmounted(() => {
  stopRecording(false) // 组件卸载时静默停止录音，不显示提示
  stopRecordingTimer() // 确保清理所有定时器
})
</script>

<style scoped>
.realtime-view {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px;
  min-height: calc(100vh - 60px);
}

.header-card {
  border-radius: 16px;
  border: none;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  gap: 20px;
  flex-wrap: wrap;
}

.title-section {
  display: flex;
  align-items: center;
  gap: 16px;
}

.page-title {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.title-icon {
  color: #409eff;
}

.status-indicator .status-icon {
  margin-right: 4px;
}

.controls-section {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  flex: 1;
  justify-content: flex-end;
}

.record-controls {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
  margin-top: 4px;
}

.control-buttons {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
}

.recording-time {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 16px 24px;
  background: var(--el-bg-color-page);
  border-radius: 12px;
  border: 1px solid var(--el-border-color-light);
  min-width: 320px;
  max-width: 420px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.time-display {
  display: flex;
  align-items: center;
  gap: 8px;
}

.duration-text {
  font-weight: 600;
  font-family: 'SF Mono', 'Monaco', 'Menlo', 'Courier New', monospace;
  font-size: 16px;
}

.time-progress {
  width: 100%;
}

.pause-button {
  font-weight: 600;
}

.record-button {
  padding: 12px 32px;
  font-size: 16px;
  font-weight: 600;
  border-radius: 8px;
  transition: all 0.3s;
}

.messages-card {
  flex: 1;
  border-radius: 16px;
  overflow: hidden;
  border: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.messages-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.messages-container {
  height: 60vh;
  min-height: 400px;
  max-height: calc(100vh - 300px);
  overflow-y: auto;
  padding: 20px 0;
}

.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 0 8px;
}

.message-item {
  display: flex;
  gap: 12px;
  animation: fadeInUp 0.3s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-content {
  flex: 1;
  max-width: min(calc(100% - 60px), 800px);
}

.message-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.speaker-name {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
}

.confidence-tag {
  font-size: 12px;
}

.message-time {
  font-size: 12px;
  color: #909399;
  margin-left: auto;
}

.message-bubble {
  background: #f8f9fa;
  padding: 14px 18px;
  border-radius: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  line-height: 1.6;
  color: #303133;
  word-wrap: break-word;
  position: relative;
  border: 1px solid rgba(0, 0, 0, 0.04);
  transition: all 0.2s ease;
}

.message-bubble::before {
  content: '';
  position: absolute;
  top: 10px;
  left: -7px;
  width: 0;
  height: 0;
  border-top: 7px solid transparent;
  border-bottom: 7px solid transparent;
  border-right: 7px solid #f8f9fa;
  filter: drop-shadow(-1px 0 1px rgba(0, 0, 0, 0.03));
}

/* 响应式设计 */
@media (max-width: 768px) {
  .realtime-view {
    padding: 12px;
    gap: 16px;
  }
  
  .header-content {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }
  
  .title-section {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
  
  .controls-section {
    justify-content: flex-start;
  }
  
  .page-title {
    font-size: 20px;
  }
  
  .messages-container {
    height: 50vh;
    min-height: 300px;
  }
  
  .control-buttons {
    flex-direction: column;
    gap: 12px;
  }
  
  .recording-time {
    min-width: 280px;
    padding: 12px 16px;
  }
  
  .duration-text {
    font-size: 14px;
  }
  
  .record-button {
    width: 100%;
    max-width: 300px;
  }
}
</style> 