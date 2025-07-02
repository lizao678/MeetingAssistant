<template>
  <div 
    class="recording-card" 
    :class="{ 'is-processing': recording.status === 'processing' }"
    @click="$emit('click', recording)"
  >
    <!-- 卡片头部 -->
    <div class="card-header">
      <div class="title-section">
        <h3 class="card-title" :title="recording.title">
          {{ recording.title }}
        </h3>
        <div class="meta-info">
          <span class="create-time">{{ formatDate(recording.createTime) }}</span>
          <span class="duration">{{ recording.duration }}</span>
        </div>
      </div>
      
      <!-- 状态指示器 -->
      <div class="status-section">
        <el-tag 
          :type="getStatusType(recording.status)" 
          size="small" 
          effect="plain"
          class="status-tag"
        >
          <template v-if="recording.status === 'processing'">
            <el-icon class="is-loading"><Loading /></el-icon>
          </template>
          {{ getStatusText(recording.status) }}
        </el-tag>
      </div>
    </div>

    <!-- 录音信息 -->
    <div class="recording-info">
      <div class="info-item">
        <el-icon><User /></el-icon>
        <span>{{ recording.speakerCount }}人参与</span>
      </div>
             <div class="info-item">
         <el-icon><Microphone /></el-icon>
         <span>{{ formatFileSize(recording.fileSize) }}</span>
       </div>
      <div class="info-item">
        <el-icon><ChatLineRound /></el-icon>
        <span>{{ recording.language || '中文' }}</span>
      </div>
    </div>

    <!-- AI摘要预览 -->
    <div v-if="recording.summary" class="summary-preview">
      <div class="summary-label">
        <el-icon><Document /></el-icon>
        智能摘要
      </div>
      <p class="summary-text">{{ recording.summary.content }}</p>
      <div v-if="recording.summary.quality" class="summary-quality">
        <span class="quality-label">质量评分：</span>
        <el-rate 
          v-model="recording.summary.quality" 
          disabled 
          size="small"
          :max="5"
          class="quality-rate"
        />
      </div>
    </div>

    <!-- 关键词标签 -->
    <div v-if="recording.keywords && recording.keywords.length > 0" class="keywords-section">
      <el-tag
        v-for="keyword in recording.keywords.slice(0, 4)"
        :key="keyword.keyword"
        size="small"
        type="primary"
        effect="plain"
        class="keyword-tag"
      >
        {{ keyword.keyword }}
      </el-tag>
      <span v-if="recording.keywords.length > 4" class="more-keywords">
        +{{ recording.keywords.length - 4 }}
      </span>
    </div>

    <!-- 处理进度 -->
    <div v-if="recording.status === 'processing'" class="processing-info">
      <el-progress 
        :percentage="processingProgress" 
        :stroke-width="4"
        class="progress-bar"
      />
      <span class="progress-text">{{ processingText }}</span>
    </div>

    <!-- 卡片底部操作 -->
    <div class="card-footer">
      <div class="left-actions">
        <el-button 
          text 
          size="small" 
          :icon="VideoPlay"
          @click.stop="$emit('play', recording)"
          :disabled="recording.status !== 'completed'"
        >
          播放
        </el-button>
        <el-button 
          text 
          size="small" 
          :icon="View"
          @click.stop="$emit('view', recording)"
        >
          详情
        </el-button>
      </div>

      <div class="right-actions">
        <el-dropdown trigger="click" @click.stop>
          <el-button text size="small" :icon="MoreFilled" />
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item 
                :icon="Download" 
                @click="$emit('download', recording)"
                :disabled="recording.status !== 'completed'"
              >
                下载录音
              </el-dropdown-item>
              <el-dropdown-item 
                :icon="Edit" 
                @click="$emit('edit', recording)"
              >
                编辑标题
              </el-dropdown-item>
              <el-dropdown-item 
                v-if="recording.status === 'completed'" 
                :icon="Refresh" 
                @click="$emit('reprocess', recording)"
              >
                离线重识别
              </el-dropdown-item>
              <el-dropdown-item 
                v-if="recording.status === 'completed'" 
                :icon="Star" 
                @click="$emit('regenerate-summary', recording)"
              >
                重新生成摘要
              </el-dropdown-item>
              <el-dropdown-item 
                divided
                :icon="Delete" 
                @click="$emit('delete', recording)"
                class="danger-item"
              >
                删除录音
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- 点击遮罩 -->
    <div class="click-overlay"></div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { 
  User, Microphone, ChatLineRound, Document, VideoPlay, View, 
  Download, Edit, Refresh, Star, Delete, MoreFilled, Loading 
} from '@element-plus/icons-vue'
import type { RecordingDetail } from '@/types/audio'

interface Props {
  recording: RecordingDetail
}

const props = defineProps<Props>()

const emit = defineEmits<{
  click: [recording: RecordingDetail]
  play: [recording: RecordingDetail]
  view: [recording: RecordingDetail]
  download: [recording: RecordingDetail]
  edit: [recording: RecordingDetail]
  reprocess: [recording: RecordingDetail]
  'regenerate-summary': [recording: RecordingDetail]
  delete: [recording: RecordingDetail]
}>()

// 模拟处理进度
const processingProgress = ref(Math.floor(Math.random() * 80) + 10)
const processingText = computed(() => {
  if (processingProgress.value < 30) return '音频转写中...'
  if (processingProgress.value < 60) return '说话人识别中...'
  if (processingProgress.value < 80) return 'AI分析中...'
  return '生成摘要中...'
})

// 格式化日期
const formatDate = (dateString: string) => {
  const date = new Date(dateString)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))
  
  if (days === 0) {
    return '今天 ' + date.toLocaleTimeString('zh-CN', { 
      hour: '2-digit', 
      minute: '2-digit' 
    })
  } else if (days === 1) {
    return '昨天 ' + date.toLocaleTimeString('zh-CN', { 
      hour: '2-digit', 
      minute: '2-digit' 
    })
  } else if (days < 7) {
    return `${days}天前`
  } else {
    return date.toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }
}

// 格式化文件大小
const formatFileSize = (bytes: number) => {
  if (!bytes) return '-'
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i]
}

// 获取状态类型
const getStatusType = (status: string) => {
  switch (status) {
    case 'completed': return 'success'
    case 'processing': return 'warning'
    case 'failed': return 'danger'
    default: return 'info'
  }
}

// 获取状态文本
const getStatusText = (status: string) => {
  switch (status) {
    case 'completed': return '已完成'
    case 'processing': return '处理中'
    case 'failed': return '处理失败'
    default: return '未知状态'
  }
}
</script>

<style scoped>
.recording-card {
  position: relative;
  background: white;
  border-radius: 16px;
  padding: 20px;
  border: 2px solid #f0f2f5;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
}

.recording-card:hover {
  border-color: #409eff;
  box-shadow: 0 12px 32px rgba(64, 158, 255, 0.15);
  transform: translateY(-4px);
}

.recording-card.is-processing {
  background: linear-gradient(135deg, #fff9e6 0%, #ffffff 100%);
  border-color: #e6a23c;
}

/* 卡片头部 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}

.title-section {
  flex: 1;
  min-width: 0;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  color: #1d2129;
  margin: 0 0 8px 0;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.meta-info {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 13px;
  color: #86909c;
}

.status-section {
  margin-left: 16px;
}

.status-tag {
  border-radius: 20px;
  padding: 4px 12px;
  font-weight: 500;
}

.status-tag .el-icon {
  margin-right: 4px;
}

/* 录音信息 */
.recording-info {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: #f7f8fa;
  border-radius: 12px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #4e5969;
}

.info-item .el-icon {
  font-size: 14px;
  color: #86909c;
}

/* AI摘要预览 */
.summary-preview {
  margin-bottom: 16px;
  padding: 16px;
  background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
  border-radius: 12px;
  border-left: 4px solid #0ea5e9;
}

.summary-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 600;
  color: #0c4a6e;
  margin-bottom: 8px;
}

.summary-text {
  font-size: 14px;
  color: #374151;
  line-height: 1.6;
  margin: 0 0 8px 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

.summary-quality {
  display: flex;
  align-items: center;
  gap: 8px;
}

.quality-label {
  font-size: 12px;
  color: #6b7280;
}

.quality-rate {
  margin: 0;
}

/* 关键词区域 */
.keywords-section {
  margin-bottom: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.keyword-tag {
  margin: 0;
  border-radius: 20px;
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #1e40af;
}

.more-keywords {
  font-size: 12px;
  color: #86909c;
  margin-left: 4px;
}

/* 处理进度 */
.processing-info {
  margin-bottom: 16px;
  padding: 12px;
  background: #fef3c7;
  border-radius: 8px;
}

.progress-bar {
  margin-bottom: 8px;
}

.progress-text {
  font-size: 12px;
  color: #92400e;
  display: flex;
  align-items: center;
  gap: 6px;
}

/* 卡片底部 */
.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 16px;
  border-top: 1px solid #f0f2f5;
}

.left-actions,
.right-actions {
  display: flex;
  gap: 8px;
}

.left-actions .el-button {
  color: #409eff;
  font-weight: 500;
}

.left-actions .el-button:hover {
  background: #ecf5ff;
}

.left-actions .el-button:disabled {
  color: #c0c4cc;
}

/* 点击遮罩 */
.click-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1;
  background: transparent;
}

.card-footer {
  position: relative;
  z-index: 2;
}

/* 下拉菜单危险项 */
:deep(.danger-item) {
  color: #f56c6c;
}

:deep(.danger-item:hover) {
  background-color: #fef0f0;
  color: #f56c6c;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .recording-card {
    padding: 16px;
  }
  
  .card-title {
    font-size: 16px;
  }
  
  .recording-info {
    flex-direction: column;
    gap: 8px;
  }
  
  .info-item {
    font-size: 12px;
  }
}
</style> 