<template>
  <div class="audio-player">
    <div class="player-container">
      <!-- 左侧播放控制 -->
      <div class="play-controls">
        <el-button
          :icon="isPlaying ? 'VideoPause' : 'VideoPlay'"
          :type="isPlaying ? 'warning' : 'primary'"
          size="large"
          circle
          @click="togglePlay"
          :disabled="!audioUrl"
        />
        
        <div class="time-info">
          <span class="current-time">{{ formatTime(currentTime) }}</span>
          <span class="separator">/</span>
          <span class="total-time">{{ formatTime(duration) }}</span>
        </div>
      </div>

      <!-- 中间进度区域 -->
      <div class="progress-section">
        <!-- 波形显示区域 -->
        <div ref="waveformContainer" class="waveform-container">
          <div v-if="!audioUrl" class="waveform-placeholder">
            <el-icon size="24" color="#c0c4cc"><Headphone /></el-icon>
            <span>暂无音频文件</span>
          </div>
        </div>
        
        <!-- 进度条 -->
        <div class="progress-bar">
          <el-slider
            v-model="progressPercent"
            :show-tooltip="false"
            :disabled="!audioUrl"
            @change="handleProgressChange"
            @input="handleProgressInput"
            class="audio-slider"
          />
        </div>
      </div>

      <!-- 右侧控制选项 -->
      <div class="player-options">
        <!-- 跳转控制 -->
        <div class="skip-controls">
          <el-button
            :icon="'DArrowLeft'"
            size="small"
            circle
            @click="skipBackward"
            :disabled="!audioUrl"
            title="后退15秒"
          />
          <el-button
            :icon="'DArrowRight'"
            size="small"
            circle
            @click="skipForward"
            :disabled="!audioUrl"
            title="前进15秒"
          />
        </div>

        <!-- 播放速度 -->
        <el-dropdown trigger="click" @command="changePlaybackRate">
          <el-button size="small" text>
            {{ playbackRate }}x
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item 
                v-for="rate in playbackRates" 
                :key="rate"
                :command="rate"
                :class="{ 'is-active': playbackRate === rate }"
              >
                {{ rate }}x
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>

        <!-- 音量控制 -->
        <div class="volume-control">
          <el-button
            :icon="volume === 0 ? 'Mute' : 'VideoPlay'"
            size="small"
            text
            @click="toggleMute"
          />
          <el-slider
            v-model="volume"
            :max="100"
            :show-tooltip="false"
            @change="handleVolumeChange"
            style="width: 80px; margin-left: 8px;"
            size="small"
          />
        </div>
      </div>
    </div>

    <!-- 段落快速跳转 -->
    <div v-if="segments.length > 0" class="segments-timeline">
      <div class="timeline-container">
        <div
          v-for="segment in segments"
          :key="segment.id"
          class="segment-marker"
          :style="{
            left: getSegmentPosition(segment.startTime) + '%',
            width: getSegmentWidth(segment.startTime, segment.endTime) + '%'
          }"
          :class="{
            'active': currentSegment?.id === segment.id,
            'hover': hoveredSegment?.id === segment.id
          }"
          @click="jumpToTime(segment.startTime)"
          @mouseenter="hoveredSegment = segment"
          @mouseleave="hoveredSegment = null"
          :title="`${segment.speakerName}: ${segment.text.substring(0, 50)}...`"
        >
          <div class="segment-color" :style="{ backgroundColor: segment.speakerColor }"></div>
        </div>
      </div>
    </div>

    <!-- 隐藏的音频元素 -->
    <audio
      ref="audioElement"
      :src="audioUrl"
      @loadedmetadata="handleLoadedMetadata"
      @timeupdate="handleTimeUpdate"
      @ended="handleEnded"
      @error="handleError"
      preload="metadata"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'

interface Segment {
  id: number
  speakerName: string
  speakerNumber: number
  speakerColor: string
  startTime: number
  endTime: number
  text: string
}

interface Props {
  audioUrl?: string
  segments?: Segment[]
  currentTime?: number
}

interface Emits {
  (e: 'time-update', time: number): void
  (e: 'segment-play', segmentId: number): void
  (e: 'play-state-change', isPlaying: boolean): void
}

const props = withDefaults(defineProps<Props>(), {
  audioUrl: '',
  segments: () => [],
  currentTime: 0
})

const emit = defineEmits<Emits>()

// 音频元素和容器引用
const audioElement = ref<HTMLAudioElement>()
const waveformContainer = ref<HTMLElement>()

// 播放状态
const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const volume = ref(100)
const playbackRate = ref(1)
const isUserSeeking = ref(false)

// 播放配置
const playbackRates = [0.5, 0.75, 1, 1.25, 1.5, 2]

// 段落相关
const currentSegment = ref<Segment | null>(null)
const hoveredSegment = ref<Segment | null>(null)

// 进度百分比
const progressPercent = computed({
  get: () => {
    if (duration.value === 0) return 0
    return (currentTime.value / duration.value) * 100
  },
  set: (value) => {
    if (duration.value > 0) {
      currentTime.value = (value / 100) * duration.value
    }
  }
})

// 方法
const togglePlay = () => {
  if (!audioElement.value || !props.audioUrl) return
  
  if (isPlaying.value) {
    audioElement.value.pause()
  } else {
    audioElement.value.play().catch(error => {
      ElMessage.error('播放失败: ' + error.message)
    })
  }
}

const skipBackward = () => {
  if (!audioElement.value) return
  audioElement.value.currentTime = Math.max(0, audioElement.value.currentTime - 15)
}

const skipForward = () => {
  if (!audioElement.value) return
  audioElement.value.currentTime = Math.min(duration.value, audioElement.value.currentTime + 15)
}

const changePlaybackRate = (rate: number) => {
  if (!audioElement.value) return
  playbackRate.value = rate
  audioElement.value.playbackRate = rate
}

const toggleMute = () => {
  if (volume.value === 0) {
    volume.value = 100
  } else {
    volume.value = 0
  }
}

const handleVolumeChange = (value: number) => {
  if (!audioElement.value) return
  audioElement.value.volume = value / 100
}

const handleProgressChange = (value: number) => {
  if (!audioElement.value) return
  const time = (value / 100) * duration.value
  audioElement.value.currentTime = time
  isUserSeeking.value = false
}

const handleProgressInput = () => {
  isUserSeeking.value = true
}

const jumpToTime = (time: number) => {
  if (!audioElement.value) return
  audioElement.value.currentTime = time
  
  // 找到对应的段落
  const segment = props.segments.find(s => time >= s.startTime && time <= s.endTime)
  if (segment) {
    emit('segment-play', segment.id)
  }
}

const formatTime = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

const getSegmentPosition = (startTime: number) => {
  if (duration.value === 0) return 0
  return (startTime / duration.value) * 100
}

const getSegmentWidth = (startTime: number, endTime: number) => {
  if (duration.value === 0) return 0
  return ((endTime - startTime) / duration.value) * 100
}

// 音频事件处理
const handleLoadedMetadata = () => {
  if (!audioElement.value) return
  duration.value = audioElement.value.duration
  audioElement.value.volume = volume.value / 100
  audioElement.value.playbackRate = playbackRate.value
}

const handleTimeUpdate = () => {
  if (!audioElement.value || isUserSeeking.value) return
  
  currentTime.value = audioElement.value.currentTime
  emit('time-update', currentTime.value)
  
  // 更新当前段落
  const segment = props.segments.find(s => 
    currentTime.value >= s.startTime && currentTime.value <= s.endTime
  )
  
  if (segment && segment.id !== currentSegment.value?.id) {
    currentSegment.value = segment
    emit('segment-play', segment.id)
  }
}

const handleEnded = () => {
  isPlaying.value = false
  emit('play-state-change', false)
}

const handleError = (error: Event) => {
  const audioEl = error.target as HTMLAudioElement
  const errorCode = audioEl.error?.code
  const errorMessage = audioEl.error?.message
  
  // 如果没有设置音频URL，不显示错误（避免初始化时的误报）
  if (!props.audioUrl || props.audioUrl === '') {
    console.debug('Audio error ignored: no audio URL set')
    return
  }
  
  // 只记录到控制台，不立即弹出错误提示
  console.warn('Audio error details:', {
    code: errorCode,
    message: errorMessage,
    src: audioEl.src,
    error: error
  })
  
  // 只有在用户尝试播放时出错才显示错误提示
  if (isPlaying.value) {
    let userMessage = '音频播放失败'
    
    // 根据错误代码提供更具体的错误信息
    switch (errorCode) {
      case 1: // MEDIA_ERR_ABORTED
        userMessage = '音频播放被中止'
        break
      case 2: // MEDIA_ERR_NETWORK
        userMessage = '网络错误，无法播放音频'
        break
      case 3: // MEDIA_ERR_DECODE
        userMessage = '音频文件已损坏，无法播放'
        break
      case 4: // MEDIA_ERR_SRC_NOT_SUPPORTED
        userMessage = '当前浏览器不支持此音频格式'
        break
      default:
        userMessage = `音频播放失败: ${errorMessage || '未知错误'}`
    }
    
    ElMessage.error(userMessage)
  }
}

// 监听播放状态
watch(() => audioElement.value, (audio) => {
  if (!audio) return
  
  const onPlay = () => {
    isPlaying.value = true
    emit('play-state-change', true)
  }
  
  const onPause = () => {
    isPlaying.value = false
    emit('play-state-change', false)
  }
  
  audio.addEventListener('play', onPlay)
  audio.addEventListener('pause', onPause)
  
  return () => {
    audio.removeEventListener('play', onPlay)
    audio.removeEventListener('pause', onPause)
  }
})

// 监听音量变化
watch(volume, (newVolume) => {
  if (audioElement.value) {
    audioElement.value.volume = newVolume / 100
  }
})

// 监听外部时间变化
watch(() => props.currentTime, (newTime) => {
  if (audioElement.value && Math.abs(newTime - currentTime.value) > 1) {
    audioElement.value.currentTime = newTime
  }
})

// 生命周期
onMounted(() => {
  // 初始化WaveSurfer等波形显示库
  // TODO: 如果需要波形显示，可以在这里初始化WaveSurfer.js
})

onUnmounted(() => {
  if (audioElement.value) {
    audioElement.value.pause()
  }
})
</script>

<style scoped>
.audio-player {
  background: white;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.player-container {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 12px;
}

.play-controls {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.time-info {
  display: flex;
  align-items: center;
  gap: 4px;
  font-family: 'SF Mono', 'Monaco', 'Menlo', 'Courier New', monospace;
  font-size: 14px;
  color: #606266;
  min-width: 100px;
}

.separator {
  color: #c0c4cc;
}

.progress-section {
  flex: 1;
  min-width: 200px;
}

.waveform-container {
  height: 60px;
  margin-bottom: 8px;
  background: #f8f9fa;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #e4e7ed;
}

.waveform-placeholder {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #c0c4cc;
  font-size: 14px;
}

.progress-bar {
  margin-top: 8px;
}

.audio-slider {
  margin: 0;
}

.audio-slider :deep(.el-slider__runway) {
  background-color: #e4e7ed;
  height: 6px;
}

.audio-slider :deep(.el-slider__bar) {
  background-color: #409eff;
  height: 6px;
}

.audio-slider :deep(.el-slider__button) {
  width: 16px;
  height: 16px;
  border: 2px solid #409eff;
}

.player-options {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-shrink: 0;
}

.skip-controls {
  display: flex;
  gap: 4px;
}

.volume-control {
  display: flex;
  align-items: center;
  min-width: 120px;
}

.segments-timeline {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #f0f0f0;
}

.timeline-container {
  position: relative;
  height: 24px;
  background: #f8f9fa;
  border-radius: 4px;
  overflow: hidden;
}

.segment-marker {
  position: absolute;
  height: 100%;
  cursor: pointer;
  border-radius: 2px;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.segment-marker:hover {
  border-color: #409eff;
  z-index: 2;
  transform: scaleY(1.2);
}

.segment-marker.active {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
  z-index: 3;
}

.segment-color {
  width: 100%;
  height: 100%;
  opacity: 0.7;
  border-radius: inherit;
}

.segment-marker:hover .segment-color,
.segment-marker.active .segment-color {
  opacity: 1;
}

:deep(.el-dropdown-menu__item.is-active) {
  background-color: #ecf5ff;
  color: #409eff;
}
</style> 