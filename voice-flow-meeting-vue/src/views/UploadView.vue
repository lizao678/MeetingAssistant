<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import recordingService, { type RecordingProcessResponse } from '@/services/recordingService'

const router = useRouter()

// 上传配置
const uploadConfig = reactive({
  language: 'zh', // 识别语言
  enableSpeakerDiarization: true, // 说话人分离
  enablePunctuation: true, // 智能标点
  enableNumberConversion: true, // 数字转换
  outputFormat: 'txt', // 输出格式
  speakerCount: 0 // 预期说话人数量（0表示自动识别）
})

// 支持的语言
const languages = [
  { label: '中文', value: 'zh' },
  { label: '英语', value: 'en' },
  { label: '日语', value: 'ja' },
  { label: '韩语', value: 'ko' },
  { label: '俄语', value: 'ru' },
  { label: '法语', value: 'fr' },
  { label: '德语', value: 'de' }
]

// 输出格式选项
const outputFormats = [
  { label: 'TXT 文本', value: 'txt' },
  { label: 'Word 文档', value: 'docx' },
  { label: 'PDF 文档', value: 'pdf' },
  { label: 'SRT 字幕', value: 'srt' },
  { label: 'JSON 数据', value: 'json' }
]

// 上传文件列表
const fileList = ref([])
const uploadProgress = ref(0)
const isUploading = ref(false)
const uploadCompleted = ref(false)
const uploadResult = ref<RecordingProcessResponse | null>(null)
const selectedFile = ref<File | null>(null)

// 文件格式限制
const allowedTypes = [
  'audio/mpeg', 'audio/wav', 'audio/mp3', 'audio/flac', 'audio/aac',
  'video/mp4', 'video/avi', 'video/mov', 'video/wmv', 'video/flv'
]

// 最大文件大小 (500MB)
const maxFileSize = 500 * 1024 * 1024

// 处理文件选择
const handleFileSelect = (file: File) => {
  // 检查文件类型
  if (!allowedTypes.includes(file.type)) {
    ElMessage.error('不支持的文件格式！请上传音频或视频文件。')
    return false
  }
  
  // 检查文件大小
  if (file.size > maxFileSize) {
    ElMessage.error('文件大小不能超过 500MB！')
    return false
  }
  
  selectedFile.value = file
  ElMessage.success(`文件 "${file.name}" 已选择，请点击开始处理按钮`)
  return false // 阻止自动上传
}

// 开始处理录音
const startProcessing = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请先选择一个文件')
    return
  }
  
  try {
    isUploading.value = true
    uploadProgress.value = 0
    
    // 创建请求数据
    const requestData = {
      audioFile: selectedFile.value,
      speakerCount: uploadConfig.speakerCount,
      language: uploadConfig.language,
      smartPunctuation: uploadConfig.enablePunctuation,
      numberConversion: uploadConfig.enableNumberConversion,
      generateSummary: true,
      summaryType: 'meeting'
    }
    
    // 发送请求到后端
    const result = await recordingService.processRecording(requestData, (progress) => {
      uploadProgress.value = progress
    })
    
    uploadProgress.value = 100
    setTimeout(() => {
      isUploading.value = false
      uploadCompleted.value = true
      uploadResult.value = result
      ElMessage.success('上传完成，开始转写处理...')
    }, 500)
    
  } catch (error: any) {
    isUploading.value = false
    uploadProgress.value = 0
    // 在错误时也重置为可以重新选择文件的状态
    selectedFile.value = null
    fileList.value = []
    ElMessage.error(error.response?.data?.detail || error.message || '上传失败，请重试')
    console.error('上传失败:', error)
  }
}

// 移除文件
const handleRemove = (file: any, fileListArray: any[]) => {
  selectedFile.value = null
  uploadCompleted.value = false
  uploadResult.value = null
  ElMessage.info('文件已移除')
}

// 文件超出限制
const handleExceed = () => {
  ElMessage.warning('最多只能上传一个文件')
}

// 处理文件列表变化
const handleFileChange = (file: any, fileListArray: any[]) => {
  if (fileListArray.length > 0) {
    const latestFile = fileListArray[fileListArray.length - 1]
    if (latestFile.raw) {
      selectedFile.value = latestFile.raw
      console.log('文件已选择:', latestFile.raw.name)
    }
  } else {
    selectedFile.value = null
  }
}

// 快速配置预设
const quickConfigs = [
  {
    name: '会议记录',
    description: '多人会议，自动识别说话人',
    config: {
      language: 'zh',
      enableSpeakerDiarization: true,
      enablePunctuation: true,
      enableNumberConversion: true,
      outputFormat: 'docx',
      speakerCount: 0
    }
  },
  {
    name: '访谈录音',
    description: '一对一访谈，高精度转写',
    config: {
      language: 'zh',
      enableSpeakerDiarization: true,
      enablePunctuation: true,
      enableNumberConversion: false,
      outputFormat: 'txt',
      speakerCount: 2
    }
  },
  {
    name: '讲座课程',
    description: '单人讲述，保留完整内容',
    config: {
      language: 'zh',
      enableSpeakerDiarization: false,
      enablePunctuation: true,
      enableNumberConversion: true,
      outputFormat: 'pdf',
      speakerCount: 1
    }
  },
  {
    name: '视频字幕',
    description: '生成字幕文件，时间轴精确',
    config: {
      language: 'zh',
      enableSpeakerDiarization: false,
      enablePunctuation: true,
      enableNumberConversion: false,
      outputFormat: 'srt',
      speakerCount: 0
    }
  }
]

// 应用快速配置
const applyQuickConfig = (config: any) => {
  Object.assign(uploadConfig, config)
  ElMessage.success('配置已应用')
}

// 重置配置
const resetConfig = () => {
  uploadConfig.language = 'zh'
  uploadConfig.enableSpeakerDiarization = true
  uploadConfig.enablePunctuation = true
  uploadConfig.enableNumberConversion = true
  uploadConfig.outputFormat = 'txt'
  uploadConfig.speakerCount = 0
  ElMessage.info('配置已重置')
}

// 格式化文件大小
const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 查看处理结果
const viewResult = () => {
  if (uploadResult.value?.recording_id) {
    router.push(`/recording/${uploadResult.value.recording_id}`)
  }
}

// 重新上传
const uploadAnother = () => {
  selectedFile.value = null
  uploadCompleted.value = false
  uploadResult.value = null
  uploadProgress.value = 0
  isUploading.value = false
  fileList.value = []
  ElMessage.info('已重置，可以上传新文件')
}

// 返回首页
const goHome = () => {
  router.push('/')
}
</script>

<template>
  <div class="upload-view">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <h1 class="page-title">
            <el-icon><Upload /></el-icon>
            上传音视频
          </h1>
          <p class="page-subtitle">上传音频或视频文件，自动转写为文字</p>
        </div>
      </div>
    </div>

    <div class="upload-content">
      <el-row :gutter="24">
        <!-- 左侧：文件上传区域 -->
        <el-col :span="14">
          <el-card class="upload-card" shadow="never">
            <template #header>
              <div class="card-header">
                <h3>文件上传</h3>
                <el-text type="info">支持 MP3、WAV、MP4、AVI 等常见音视频格式</el-text>
              </div>
            </template>

            <!-- 上传组件 -->
            <div class="upload-section">
              <el-upload
                class="upload-dragger"
                drag
                :before-upload="handleFileSelect"
                :auto-upload="false"
                :on-remove="handleRemove"
                :on-exceed="handleExceed"
                :on-change="handleFileChange"
                :file-list="fileList"
                :limit="1"
                accept="audio/*,video/*"
              >
                <div class="upload-content-area">
                  <el-icon class="upload-icon" size="48">
                    <Upload />
                  </el-icon>
                  <div class="upload-text">
                    <p>将文件拖拽到此处，或<em>点击上传</em></p>
                    <p class="upload-tip">文件大小不超过 500MB</p>
                  </div>
                </div>
              </el-upload>

              <!-- 调试信息 -->
              <div v-if="!selectedFile && fileList.length > 0" class="debug-info" style="margin-top: 16px; padding: 12px; background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 4px;">
                <p style="margin: 0; color: #856404; font-size: 14px;">
                  调试信息：文件列表长度 {{ fileList.length }}，selectedFile: {{ selectedFile ? '已设置' : '未设置' }}
                </p>
              </div>

              <!-- 选中的文件信息 -->
              <div v-if="selectedFile && !isUploading && !uploadCompleted" class="selected-file-info">
                <div class="file-info">
                  <el-icon><Document /></el-icon>
                  <div class="file-details">
                    <p class="file-name">{{ selectedFile.name }}</p>
                    <p class="file-size">{{ formatFileSize(selectedFile.size) }}</p>
                  </div>
                </div>
                <el-button 
                  type="primary" 
                  size="large"
                  @click="startProcessing"
                  :disabled="isUploading"
                >
                  开始处理
                </el-button>
              </div>

              <!-- 上传进度 -->
              <div v-if="isUploading" class="upload-progress">
                <el-progress
                  :percentage="uploadProgress"
                  :stroke-width="8"
                  status="success"
                />
                <p class="progress-text">正在上传和处理文件...</p>
              </div>

              <!-- 上传完成状态 -->
              <div v-if="uploadCompleted && uploadResult" class="upload-completed">
                <div class="completion-info">
                  <el-icon class="success-icon" color="#67c23a" size="48">
                    <CircleCheck />
                  </el-icon>
                  <div class="completion-text">
                    <h3>上传成功！</h3>
                    <p>文件已成功上传并开始处理，您可以：</p>
                  </div>
                </div>
                
                <div class="completion-actions">
                  <el-button 
                    type="primary" 
                    size="large"
                    @click="viewResult"
                  >
                    <el-icon><View /></el-icon>
                    查看处理结果
                  </el-button>
                  
                  <el-button 
                    size="large"
                    @click="uploadAnother"
                  >
                    <el-icon><Upload /></el-icon>
                    上传其他文件
                  </el-button>
                  
                  <el-button 
                    size="large"
                    @click="goHome"
                  >
                    <el-icon><House /></el-icon>
                    返回首页
                  </el-button>
                </div>

                <div class="upload-result-info">
                  <el-descriptions :column="2" size="small" border>
                    <el-descriptions-item label="录音ID">
                      {{ uploadResult.recording_id }}
                    </el-descriptions-item>
                    <el-descriptions-item label="处理状态">
                      <el-tag type="success">处理中</el-tag>
                    </el-descriptions-item>
                    <el-descriptions-item label="文件名">
                      {{ selectedFile?.name }}
                    </el-descriptions-item>
                    <el-descriptions-item label="文件大小">
                      {{ selectedFile ? formatFileSize(selectedFile.size) : '-' }}
                    </el-descriptions-item>
                  </el-descriptions>
                </div>
              </div>
            </div>

            <!-- 支持格式说明 -->
            <div class="format-info">
              <h4>支持的文件格式</h4>
              <div class="format-list">
                <el-tag type="info" effect="plain">MP3</el-tag>
                <el-tag type="info" effect="plain">WAV</el-tag>
                <el-tag type="info" effect="plain">FLAC</el-tag>
                <el-tag type="info" effect="plain">AAC</el-tag>
                <el-tag type="info" effect="plain">MP4</el-tag>
                <el-tag type="info" effect="plain">AVI</el-tag>
                <el-tag type="info" effect="plain">MOV</el-tag>
                <el-tag type="info" effect="plain">WMV</el-tag>
              </div>
            </div>
          </el-card>
        </el-col>

        <!-- 右侧：配置选项 -->
        <el-col :span="10">
          <el-card class="config-card" shadow="never">
            <template #header>
              <div class="card-header">
                <h3>转写设置</h3>
                <el-button text @click="resetConfig">重置</el-button>
              </div>
            </template>

            <!-- 快速配置 -->
            <div class="quick-config-section">
              <h4>快速配置</h4>
              <div class="quick-config-grid">
                <div
                  v-for="config in quickConfigs"
                  :key="config.name"
                  class="quick-config-item"
                  @click="applyQuickConfig(config.config)"
                >
                  <h5>{{ config.name }}</h5>
                  <p>{{ config.description }}</p>
                </div>
              </div>
            </div>

            <el-divider />

            <!-- 详细配置 -->
            <div class="detail-config-section">
              <h4>详细配置</h4>
              
              <el-form :model="uploadConfig" label-width="120px" size="default">
                <el-form-item label="识别语言">
                  <el-select v-model="uploadConfig.language" style="width: 100%">
                    <el-option
                      v-for="lang in languages"
                      :key="lang.value"
                      :label="lang.label"
                      :value="lang.value"
                    />
                  </el-select>
                </el-form-item>

                <el-form-item label="说话人分离">
                  <el-switch
                    v-model="uploadConfig.enableSpeakerDiarization"
                    active-text="开启"
                    inactive-text="关闭"
                  />
                  <div class="config-tip">
                    自动识别并标记不同说话人
                  </div>
                </el-form-item>

                <el-form-item label="说话人数量" v-if="uploadConfig.enableSpeakerDiarization">
                  <el-input-number
                    v-model="uploadConfig.speakerCount"
                    :min="0"
                    :max="20"
                    style="width: 100%"
                  />
                  <div class="config-tip">
                    0 表示自动识别说话人数量
                  </div>
                </el-form-item>

                <el-form-item label="智能标点">
                  <el-switch
                    v-model="uploadConfig.enablePunctuation"
                    active-text="开启"
                    inactive-text="关闭"
                  />
                  <div class="config-tip">
                    自动添加标点符号和语句分段
                  </div>
                </el-form-item>

                <el-form-item label="数字转换">
                  <el-switch
                    v-model="uploadConfig.enableNumberConversion"
                    active-text="开启"
                    inactive-text="关闭"
                  />
                  <div class="config-tip">
                    将语音中的数字转换为阿拉伯数字
                  </div>
                </el-form-item>

                <el-form-item label="输出格式">
                  <el-select v-model="uploadConfig.outputFormat" style="width: 100%">
                    <el-option
                      v-for="format in outputFormats"
                      :key="format.value"
                      :label="format.label"
                      :value="format.value"
                    />
                  </el-select>
                </el-form-item>
              </el-form>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<style scoped>
.upload-view {
  min-height: 100vh;
  background: #f5f7fa;
}

/* 页面头部 */
.page-header {
  background: white;
  border-bottom: 1px solid #e4e7ed;
  padding: 24px 0;
}

.header-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 8px 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.page-subtitle {
  color: #606266;
  margin: 0;
  font-size: 14px;
}

/* 主要内容 */
.upload-content {
  max-width: 1200px;
  margin: 24px auto;
  padding: 0 24px;
}

/* 卡片样式 */
.upload-card,
.config-card {
  border-radius: 12px;
  border: 1px solid #e4e7ed;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

/* 上传区域 */
.upload-section {
  margin-bottom: 24px;
}

:deep(.upload-dragger) {
  width: 100%;
}

:deep(.el-upload-dragger) {
  width: 100%;
  height: 200px;
  border: 2px dashed #d9d9d9;
  border-radius: 12px;
  background: #fafafa;
  transition: all 0.3s;
}

:deep(.el-upload-dragger:hover) {
  border-color: #409eff;
  background: #f0f9ff;
}

.upload-content-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 20px;
}

.upload-icon {
  color: #c0c4cc;
  margin-bottom: 16px;
}

.upload-text p {
  margin: 0 0 8px 0;
  color: #606266;
  font-size: 16px;
}

.upload-text em {
  color: #409eff;
  font-style: normal;
}

.upload-tip {
  font-size: 14px !important;
  color: #909399 !important;
}

/* 选中文件信息 */
.selected-file-info {
  margin-top: 24px;
  padding: 20px;
  background: #f0f9ff;
  border: 1px solid #e1f5fe;
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-details .file-name {
  font-weight: 500;
  color: #303133;
  margin: 0 0 4px 0;
}

.file-details .file-size {
  font-size: 14px;
  color: #909399;
  margin: 0;
}

/* 上传进度 */
.upload-progress {
  margin-top: 24px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
}

.progress-text {
  text-align: center;
  color: #606266;
  margin: 8px 0 0 0;
}

/* 上传完成状态 */
.upload-completed {
  margin-top: 24px;
  padding: 24px;
  background: #f0f9ff;
  border: 1px solid #e1f5fe;
  border-radius: 12px;
}

.completion-info {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.completion-text h3 {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 8px 0;
}

.completion-text p {
  color: #606266;
  margin: 0;
  font-size: 14px;
}

.completion-actions {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.completion-actions .el-button {
  flex: 1;
  min-width: 140px;
}

.upload-result-info {
  margin-top: 20px;
}

/* 格式信息 */
.format-info {
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
}

.format-info h4 {
  font-size: 14px;
  color: #303133;
  margin: 0 0 12px 0;
}

.format-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

/* 快速配置 */
.quick-config-section {
  margin-bottom: 20px;
}

.quick-config-section h4 {
  font-size: 16px;
  color: #303133;
  margin: 0 0 16px 0;
}

.quick-config-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.quick-config-item {
  padding: 16px;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
  background: white;
}

.quick-config-item:hover {
  border-color: #409eff;
  background: #f0f9ff;
}

.quick-config-item h5 {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 4px 0;
}

.quick-config-item p {
  font-size: 12px;
  color: #909399;
  margin: 0;
  line-height: 1.4;
}

/* 详细配置 */
.detail-config-section h4 {
  font-size: 16px;
  color: #303133;
  margin: 0 0 20px 0;
}

.config-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  line-height: 1.4;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .upload-content .el-row {
    flex-direction: column;
  }
  
  .upload-content .el-col {
    width: 100% !important;
    margin-bottom: 16px;
  }

  .quick-config-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .upload-content {
    padding: 0 16px;
  }

  :deep(.el-upload-dragger) {
    height: 160px;
  }

  .upload-content-area {
    padding: 16px;
  }

  .upload-icon {
    font-size: 36px !important;
  }

  .upload-text p {
    font-size: 14px;
  }

  .completion-actions {
    flex-direction: column;
  }

  .completion-actions .el-button {
    min-width: auto;
  }
}
</style> 