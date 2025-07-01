<template>
  <el-dialog
    v-model="visible"
    title="录音处理设置"
    width="500px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
    destroy-on-close
    center
  >
    <div class="dialog-content">
      <!-- 录音信息 -->
      <div class="recording-info">
        <el-icon class="info-icon" size="48" color="#409eff">
          <CircleCheck />
        </el-icon>
        <div class="info-text">
          <h3>录音完成</h3>
          <p>录音时长：{{ formatDuration(recordingData.duration) }}</p>
          <p>语言：{{ getLanguageText(recordingData.language) }}</p>
        </div>
      </div>

      <!-- 发言人数选择 -->
      <div class="speaker-section">
        <h4>请选择发言人数量</h4>
        <p class="section-desc">这将帮助AI更准确地识别和区分不同的说话人</p>
        
        <div class="speaker-options">
          <el-radio-group v-model="selectedCount" class="speaker-radio-group">
            <el-radio :value="1">1人（单人讲述）</el-radio>
            <el-radio :value="2">2人（对话访谈）</el-radio>
            <el-radio :value="3">3人（小组讨论）</el-radio>
            <el-radio :value="4">4人（会议讨论）</el-radio>
            <el-radio :value="5">5人（多人会议）</el-radio>
            <el-radio :value="0">自动识别（推荐）</el-radio>
          </el-radio-group>
        </div>

        <!-- 自定义数量 -->
        <div v-if="selectedCount > 5" class="custom-count">
          <el-input-number 
            v-model="customCount" 
            :min="6" 
            :max="20" 
            controls-position="right"
            class="count-input"
          />
          <span class="count-label">人</span>
        </div>
      </div>

      <!-- 高级选项 -->
      <div class="advanced-options">
        <el-collapse v-model="activeOptions">
          <el-collapse-item title="高级选项" name="advanced">
            <div class="option-item">
              <el-checkbox v-model="options.enablePunctuation">
                智能标点符号
              </el-checkbox>
              <span class="option-desc">自动添加逗号、句号等标点</span>
            </div>
            <div class="option-item">
              <el-checkbox v-model="options.enableNumberConversion">
                数字转换
              </el-checkbox>
              <span class="option-desc">将"一百二十三"转为"123"</span>
            </div>
            <div class="option-item">
              <el-checkbox v-model="options.enableSummary">
                生成智能摘要
              </el-checkbox>
              <span class="option-desc">AI生成关键词和内容摘要</span>
            </div>
          </el-collapse-item>
        </el-collapse>
      </div>

      <!-- 处理状态 -->
      <div v-if="isProcessing" class="processing-status">
        <el-progress 
          :percentage="processingProgress" 
          :status="processingStatus"
          :show-text="true"
        />
        <p class="processing-text">{{ processingText }}</p>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button 
          @click="handleCancel" 
          :disabled="isProcessing"
          size="large"
        >
          取消
        </el-button>
        <el-button 
          type="primary" 
          @click="handleConfirm"
          :loading="isProcessing"
          size="large"
        >
          {{ isProcessing ? '处理中...' : '开始处理' }}
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'

interface RecordingData {
  duration: number
  language: string
  audioBlob?: Blob
  messages: any[]
}

interface ProcessingOptions {
  enablePunctuation: boolean
  enableNumberConversion: boolean
  enableSummary: boolean
}

interface Props {
  modelValue: boolean
  recordingData: RecordingData
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
  (e: 'confirm', data: {
    speakerCount: number
    options: ProcessingOptions
    recordingData: RecordingData
  }): void
  (e: 'cancel'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

// 响应式数据
const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const selectedCount = ref(0) // 默认自动识别
const customCount = ref(6)
const activeOptions = ref<string[]>([])

const options = ref<ProcessingOptions>({
  enablePunctuation: true,
  enableNumberConversion: true,
  enableSummary: true
})

// 处理状态
const isProcessing = ref(false)
const processingProgress = ref(0)
const processingStatus = ref<'success' | 'exception' | undefined>()
const processingText = ref('')

// 计算最终的发言人数
const finalSpeakerCount = computed(() => {
  if (selectedCount.value === 0) return 0 // 自动识别
  if (selectedCount.value > 5) return customCount.value
  return selectedCount.value
})

// 格式化时长
const formatDuration = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

// 获取语言文本
const getLanguageText = (lang: string) => {
  const langMap: Record<string, string> = {
    'zh': '中文',
    'en': '英文',
    'ja': '日语',
    'ko': '韩语',
    'yue': '粤语',
    'auto': '自动检测'
  }
  return langMap[lang] || '未知'
}

// 模拟处理进度
const simulateProcessing = () => {
  return new Promise<void>((resolve, reject) => {
    isProcessing.value = true
    processingProgress.value = 0
    processingText.value = '正在上传录音文件...'
    
    const progressSteps = [
      { progress: 20, text: '正在上传录音文件...' },
      { progress: 40, text: '正在进行语音识别...' },
      { progress: 60, text: '正在识别说话人...' },
      { progress: 80, text: '正在生成智能摘要...' },
      { progress: 100, text: '处理完成！' }
    ]
    
    let stepIndex = 0
    const interval = setInterval(() => {
      if (stepIndex < progressSteps.length) {
        const step = progressSteps[stepIndex]
        processingProgress.value = step.progress
        processingText.value = step.text
        stepIndex++
      } else {
        clearInterval(interval)
        processingStatus.value = 'success'
        setTimeout(() => {
          resolve()
        }, 500)
      }
    }, 800)
    
    // 模拟可能的错误（用于测试）
    setTimeout(() => {
      if (Math.random() < 0.05) { // 5% 概率出错
        clearInterval(interval)
        processingStatus.value = 'exception'
        processingText.value = '处理失败，请重试'
        reject(new Error('处理失败'))
      }
    }, 1000)
  })
}

// 确认处理
const handleConfirm = async () => {
  try {
    // 验证数据
    if (!props.recordingData.duration || props.recordingData.duration < 1) {
      ElMessage.warning('录音时长太短，请重新录制')
      return
    }
    
    // 开始处理
    await simulateProcessing()
    
    // 发送数据
    emit('confirm', {
      speakerCount: finalSpeakerCount.value,
      options: options.value,
      recordingData: props.recordingData
    })
    
    ElMessage.success('录音处理完成！')
    visible.value = false
    
  } catch (error) {
    ElMessage.error('处理失败，请重试')
    isProcessing.value = false
    processingStatus.value = undefined
  }
}

// 取消
const handleCancel = () => {
  if (isProcessing.value) {
    return
  }
  
  emit('cancel')
  visible.value = false
}

// 重置状态
watch(visible, (newVal) => {
  if (newVal) {
    // 对话框打开时重置状态
    selectedCount.value = 0
    customCount.value = 6
    activeOptions.value = []
    isProcessing.value = false
    processingProgress.value = 0
    processingStatus.value = undefined
    processingText.value = ''
    
    options.value = {
      enablePunctuation: true,
      enableNumberConversion: true,
      enableSummary: true
    }
  }
})
</script>

<style scoped>
.dialog-content {
  padding: 16px 0;
}

.recording-info {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 12px;
  margin-bottom: 24px;
}

.info-icon {
  flex-shrink: 0;
}

.info-text h3 {
  margin: 0 0 8px 0;
  font-size: 18px;
  color: #303133;
}

.info-text p {
  margin: 4px 0;
  color: #606266;
  font-size: 14px;
}

.speaker-section {
  margin-bottom: 24px;
}

.speaker-section h4 {
  margin: 0 0 8px 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.section-desc {
  margin: 0 0 16px 0;
  font-size: 14px;
  color: #909399;
}

.speaker-radio-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.speaker-radio-group :deep(.el-radio) {
  margin-right: 0;
  margin-bottom: 0;
}

.custom-count {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 16px;
  padding-left: 24px;
}

.count-input {
  width: 120px;
}

.count-label {
  color: #606266;
  font-size: 14px;
}

.advanced-options {
  margin-bottom: 16px;
}

.option-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.option-desc {
  font-size: 12px;
  color: #909399;
  margin-left: 8px;
}

.processing-status {
  margin-top: 16px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 8px;
}

.processing-text {
  margin: 12px 0 0 0;
  text-align: center;
  font-size: 14px;
  color: #606266;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

:deep(.el-dialog__header) {
  padding: 20px 20px 0 20px;
}

:deep(.el-dialog__body) {
  padding: 20px;
}

:deep(.el-dialog__footer) {
  padding: 0 20px 20px 20px;
}
</style> 