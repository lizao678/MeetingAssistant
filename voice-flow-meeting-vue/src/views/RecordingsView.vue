<template>
  <div class="recordings-view">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <h1 class="page-title">
            <el-icon><Folder /></el-icon>
            我的记录
          </h1>
          <p class="page-subtitle">管理您的所有录音文件和转写记录</p>
        </div>
        <div class="header-actions">
          <el-button type="primary" :icon="'Plus'" @click="router.push('/realtime')">
            新建录音
          </el-button>
        </div>
      </div>
    </div>

    <!-- 筛选和搜索 -->
    <div class="filter-section">
      <div class="filter-content">
        <el-row :gutter="16" align="middle">
          <el-col :span="8">
            <el-input
              v-model="searchText"
              placeholder="搜索录音标题或描述..."
              :prefix-icon="'Search'"
              clearable
            />
          </el-col>
          <el-col :span="4">
            <el-select
              v-model="selectedStatus"
              placeholder="状态筛选"
              clearable
            >
              <el-option
                v-for="option in statusOptions"
                :key="option.value"
                :label="option.label"
                :value="option.value"
              />
            </el-select>
          </el-col>
          <el-col :span="6">
            <el-date-picker
              v-model="selectedDateRange"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              size="default"
            />
          </el-col>
          <el-col :span="6">
            <div class="view-controls">
              <el-tooltip content="网格视图" placement="top">
                <el-button :icon="'Grid'" type="primary" plain size="small" />
              </el-tooltip>
              <el-tooltip content="列表视图" placement="top">
                <el-button :icon="'List'" plain size="small" />
              </el-tooltip>
            </div>
          </el-col>
        </el-row>
      </div>
    </div>

    <!-- 录音列表 -->
    <div class="recordings-section">
      <div class="recordings-grid">
        <div
          v-for="recording in filteredRecordings"
          :key="recording.id"
          class="recording-card"
          @click="viewDetails(recording)"
        >
          <!-- 卡片头部 -->
          <div class="card-header">
            <div class="title-section">
              <h3 class="card-title">{{ recording.title }}</h3>
              <span class="recording-time">{{ recording.createTime }}</span>
            </div>
            <div class="actions-section">
              <el-button
                text
                size="small"
                :icon="'VideoPlay'"
                @click.stop="playRecording(recording)"
                class="play-btn"
              />
              <el-dropdown trigger="click" @click.stop>
                <el-button text size="small" :icon="'MoreFilled'" />
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item :icon="'View'" @click="viewDetails(recording)">
                      查看详情
                    </el-dropdown-item>
                    <el-dropdown-item :icon="'Download'" @click="downloadRecording(recording)">
                      下载录音
                    </el-dropdown-item>
                    <el-dropdown-item 
                      v-if="recording.status === 'failed'" 
                      :icon="'Refresh'" 
                      @click="reprocess(recording)"
                    >
                      重新处理
                    </el-dropdown-item>
                    <el-dropdown-item 
                      :icon="'Delete'" 
                      @click="deleteRecording(recording)"
                      class="danger-item"
                    >
                      删除录音
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>

          <!-- 录音时长 -->
          <div class="duration-info">
            <span class="duration">{{ recording.duration }}</span>
          </div>

          <!-- 关键词标签 -->
          <div v-if="recording.tags.length > 0" class="keywords-section">
            <el-tag
              v-for="tag in recording.tags"
              :key="tag"
              size="small"
              type="primary"
              effect="plain"
              class="keyword-tag"
            >
              {{ tag }}
            </el-tag>
          </div>

          <!-- 录音内容预览 -->
          <div class="content-preview">
            <p>{{ recording.preview }}</p>
          </div>

          <!-- 卡片底部信息 -->
          <div class="card-footer">
            <div class="footer-meta">
              <span class="time-info">{{ recording.createTime.split(' ')[1] }}</span>
              <span class="meta-separator">·</span>
              <span class="duration-info">时长 {{ recording.createTime.split(' ')[0] }}</span>
            </div>
            <div class="status-badges">
              <el-tag
                v-if="recording.hasTranscript"
                size="small"
                type="success"
                effect="plain"
              >
                转写
              </el-tag>
              <el-tag
                v-if="recording.hasSummary"
                size="small"
                type="primary"
                effect="plain"
              >
                总结
              </el-tag>
              <el-tag
                :type="getStatusType(recording.status)"
                size="small"
                effect="plain"
              >
                {{ getStatusText(recording.status) }}
              </el-tag>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-if="filteredRecordings.length === 0 && recordings.length > 0" class="empty-state">
      <el-empty description="没有符合条件的录音记录">
        <el-button type="primary" @click="searchText = ''; selectedStatus = ''">
          清除筛选条件
        </el-button>
      </el-empty>
    </div>

    <div v-if="recordings.length === 0" class="empty-state">
      <el-empty description="还没有录音记录">
        <el-button type="primary" @click="router.push('/realtime')">
          立即开始录音
        </el-button>
      </el-empty>
    </div>

    <!-- 录音详情弹窗 -->
    <el-dialog
      v-model="detailsVisible"
      :title="currentRecording?.title"
      width="90%"
      class="recording-details-dialog"
      @close="closeDetails"
    >
      <div v-if="currentRecording" class="recording-details">
        <!-- 录音信息头部 -->
        <div class="details-header">
          <div class="recording-meta-info">
            <div class="meta-item">
              <el-icon><Clock /></el-icon>
              <span>{{ currentRecording.duration }}</span>
            </div>
            <div class="meta-item">
              <el-icon><Files /></el-icon>
              <span>{{ currentRecording.fileSize }}</span>
            </div>
            <div class="meta-item">
              <el-icon><User /></el-icon>
              <span>{{ currentRecording.speakerCount }}人参与</span>
            </div>
            <div class="meta-item">
              <el-icon><Calendar /></el-icon>
              <span>{{ currentRecording.createTime }}</span>
            </div>
          </div>
          <div class="header-actions">
            <el-button :icon="'Download'" @click="downloadRecording(currentRecording)">
              下载录音
            </el-button>
          </div>
        </div>

        <!-- 功能标签页 -->
        <el-tabs v-model="activeTab" class="details-tabs">
          <!-- 智能速览 -->
          <el-tab-pane label="智能速览" name="summary">
            <div class="tab-content">
              <div v-if="currentRecording.hasSummary" class="summary-section">
                <!-- 关键词 -->
                <div class="summary-block">
                  <h3>关键词</h3>
                  <div class="keywords-container">
                    <el-tag
                      v-for="keyword in mockSummaryData.keywords"
                      :key="keyword"
                      type="primary"
                      effect="plain"
                      class="keyword-tag"
                    >
                      {{ keyword }}
                    </el-tag>
                  </div>
                </div>

                <!-- 全文概要 -->
                <div class="summary-block">
                  <h3>全文概要</h3>
                  <div class="summary-text">
                    {{ mockSummaryData.summary }}
                  </div>
                </div>

                <!-- 发言总结 -->
                <div class="summary-block">
                  <h3>发言总结</h3>
                  <div class="speaker-summaries">
                    <div
                      v-for="speaker in mockSummaryData.speakerSummaries"
                      :key="speaker.id"
                      class="speaker-summary"
                    >
                      <div class="speaker-header">
                        <el-avatar :size="32">{{ speaker.name }}</el-avatar>
                        <span class="speaker-name">{{ speaker.name }}</span>
                        <span class="speaker-time">发言时长: {{ speaker.duration }}</span>
                      </div>
                      <div class="speaker-content">
                        {{ speaker.summary }}
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 待办事项 -->
                <div v-if="mockSummaryData.todos.length > 0" class="summary-block">
                  <h3>待办事项</h3>
                  <div class="todos-list">
                    <div
                      v-for="(todo, index) in mockSummaryData.todos"
                      :key="index"
                      class="todo-item"
                    >
                      <el-icon><Check /></el-icon>
                      <span>{{ todo }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="no-summary">
                <el-empty description="暂无智能总结">
                  <el-button type="primary" @click="generateSummary">
                    生成智能总结
                  </el-button>
                </el-empty>
              </div>
            </div>
          </el-tab-pane>

          <!-- 原文 -->
          <el-tab-pane label="原文" name="transcript">
            <div class="tab-content">
              <div v-if="currentRecording.hasTranscript" class="transcript-section">
                <!-- 播放控制 -->
                <div class="audio-controls">
                  <el-button-group>
                    <el-button :icon="isPlaying ? 'VideoPause' : 'VideoPlay'" @click="togglePlay">
                      {{ isPlaying ? '暂停' : '播放' }}
                    </el-button>
                    <el-button :icon="'RefreshLeft'" @click="seekTo(0)">
                      重播
                    </el-button>
                  </el-button-group>
                  <div class="time-info">
                    <span>{{ formatTime(currentTime) }}</span>
                    <span>/</span>
                    <span>{{ formatTime(totalTime) }}</span>
                  </div>
                </div>

                <!-- 转写文本 -->
                <div class="transcript-content">
                  <div
                    v-for="segment in mockTranscriptData"
                    :key="segment.id"
                    class="transcript-segment"
                    :class="{ active: segment.id === activeSegment }"
                    @click="seekToSegment(segment)"
                  >
                    <div class="segment-header">
                      <el-avatar :size="24">{{ segment.speaker }}</el-avatar>
                      <span class="speaker-name">{{ segment.speaker }}</span>
                      <span class="segment-time">{{ segment.startTime }}</span>
                    </div>
                    <div class="segment-text">
                      {{ segment.text }}
                    </div>
                  </div>
                </div>
              </div>
              <div v-else class="no-transcript">
                <el-empty description="暂无转写文本">
                  <el-button type="primary" @click="generateTranscript">
                    开始转写
                  </el-button>
                </el-empty>
              </div>
            </div>
          </el-tab-pane>

          <!-- 待办事项 -->
          <el-tab-pane label="待办事项" name="todos">
            <div class="tab-content">
              <div class="todos-section">
                <div class="todos-header">
                  <h3>从会议中提取的待办事项</h3>
                  <el-button type="primary" size="small" @click="addTodo">
                    添加待办
                  </el-button>
                </div>
                <div v-if="mockSummaryData.todos.length > 0" class="todos-list">
                  <div
                    v-for="(todo, index) in mockSummaryData.todos"
                    :key="index"
                    class="todo-item-detailed"
                  >
                    <el-checkbox>{{ todo }}</el-checkbox>
                    <el-button text size="small" :icon="'Delete'" class="delete-todo" />
                  </div>
                </div>
                <div v-else class="no-todos">
                  <el-empty description="暂无待办事项" />
                </div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()

// 搜索和筛选
const searchText = ref('')
const selectedDateRange = ref('')
const selectedStatus = ref('')

// 模拟录音数据
const recordings = ref([
  {
    id: '1',
    title: '项目讨论会议',
    description: '关于新产品功能规划的讨论',
    duration: '45:32',
    fileSize: '128 MB',
    createTime: '2025-01-30 16:11',
    updateTime: '2025-01-30 16:56',
    status: 'completed',
    language: '中文',
    speakerCount: 3,
    tags: ['会议', '产品规划', '功能讨论'],
    hasTranscript: true,
    hasSummary: true,
    preview: '大家好，今天我们主要讨论新产品的功能规划。根据最近的用户调研结果，我们发现用户对于语音识别功能有很强的需求。从技术角度来看，语音识别的准确率是关键，我们需要考虑不同场景下的识别效果。'
  },
  {
    id: '2',
    title: '客户访谈记录',
    description: '用户体验调研访谈',
    duration: '28:45',
    fileSize: '86 MB',
    createTime: '2025-01-30 10:38',
    updateTime: '2025-01-30 11:06',
    status: 'completed',
    language: '中文',
    speakerCount: 2,
    tags: ['访谈', '用户体验', '调研'],
    hasTranscript: true,
    hasSummary: true,
    preview: '感谢您参与我们的用户体验访谈。首先想了解一下您在使用类似产品时遇到的主要问题是什么？在日常工作中，您对语音转写的准确性有什么期望？希望能够在哪些场景下使用这个功能？'
  },
  {
    id: '3',
    title: '团队周会',
    description: '周度工作总结与计划',
    duration: '32:18',
    fileSize: '95 MB',
    createTime: '2025-01-29 14:20',
    updateTime: '2025-01-29 14:52',
    status: 'completed',
    language: '中文',
    speakerCount: 5,
    tags: ['周会', '工作总结', '计划'],
    hasTranscript: true,
    hasSummary: false,
    preview: '本周工作总结：前端开发进度良好，UI界面基本完成。后端API接口开发按计划推进，数据库设计已经确定。测试团队开始准备测试用例，预计下周开始内测。下周重点工作安排。'
  },
  {
    id: '4',
    title: '技术方案讨论',
    description: '架构设计和技术选型',
    duration: '52:09',
    fileSize: '156 MB',
    createTime: '2025-01-28 15:30',
    updateTime: '2025-01-28 16:22',
    status: 'processing',
    language: '中文',
    speakerCount: 4,
    tags: ['技术', '架构', '设计'],
    hasTranscript: false,
    hasSummary: false,
    preview: '今天我们来讨论新项目的技术架构方案。首先是前端技术选型，建议使用Vue 3 + TypeScript的组合。后端方面，考虑使用FastAPI框架，数据库使用PostgreSQL。'
  },
  {
    id: '5',
    title: '市场调研汇报',
    description: '竞品分析和市场定位',
    duration: '38:24',
    fileSize: '112 MB',
    createTime: '2025-01-27 14:39',
    updateTime: '2025-01-27 15:17',
    status: 'completed',
    language: '中文',
    speakerCount: 3,
    tags: ['市场调研', '竞品分析', '定位'],
    hasTranscript: true,
    hasSummary: true,
    preview: '通过对市场上主要竞品的深入分析，我们发现在语音识别准确率和多人对话场景下，现有产品都存在一定的改进空间。我们的产品定位应该聚焦于...'
  },
  {
    id: '6',
    title: '产品需求评审',
    description: '新功能需求讨论',
    duration: '41:15',
    fileSize: '125 MB',
    createTime: '2025-01-26 15:22',
    updateTime: '2025-01-26 16:03',
    status: 'completed',
    language: '中文',
    speakerCount: 4,
    tags: ['需求评审', '产品', '功能'],
    hasTranscript: true,
    hasSummary: false,
    preview: '今天我们来评审新版本的功能需求。第一个是实时转写功能的优化，用户反馈希望能支持更多语言。第二个是智能总结功能，需要提取关键信息...'
  }
])

// 状态选项
const statusOptions = [
  { label: '全部状态', value: '' },
  { label: '已完成', value: 'completed' },
  { label: '处理中', value: 'processing' },
  { label: '失败', value: 'failed' }
]

// 筛选后的录音列表
const filteredRecordings = computed(() => {
  return recordings.value.filter(item => {
    const matchSearch = !searchText.value || 
      item.title.toLowerCase().includes(searchText.value.toLowerCase()) ||
      item.description.toLowerCase().includes(searchText.value.toLowerCase())
    
    const matchStatus = !selectedStatus.value || item.status === selectedStatus.value
    
    return matchSearch && matchStatus
  })
})

// 获取状态标签类型
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
    case 'failed': return '失败'
    default: return '未知'
  }
}

// 播放录音
const playRecording = (item: any) => {
  ElMessage.success(`播放录音: ${item.title}`)
}

// 查看转写结果
const viewTranscript = (item: any) => {
  router.push(`/transcript/${item.id}`)
}

// 查看录音详情（包含智能总结）
const detailsVisible = ref(false)
const currentRecording = ref<any>(null)
const activeTab = ref('summary')
const isPlaying = ref(false)
const currentTime = ref(0)
const totalTime = ref(0)
const activeSegment = ref('')

const viewDetails = (item: any) => {
  currentRecording.value = item
  detailsVisible.value = true
  activeTab.value = 'summary'
  
  // 解析录音时长并设置总时间
  const durationMatch = item.duration.match(/(\d+):(\d+)/)
  if (durationMatch) {
    const minutes = parseInt(durationMatch[1])
    const seconds = parseInt(durationMatch[2])
    totalTime.value = minutes * 60 + seconds
  }
}

const closeDetails = () => {
  detailsVisible.value = false
  currentRecording.value = null
  isPlaying.value = false
}

// 模拟智能总结数据
const mockSummaryData = ref({
  keywords: ['产品规划', '用户体验', '技术方案', '市场分析', '团队协作'],
  summary: '本次会议主要讨论了新产品的功能规划和用户体验优化方案。团队就技术架构、市场定位和用户需求进行了深入交流，确定了下一阶段的开发重点和时间节点。',
  speakerSummaries: [
    {
      id: '1',
      name: '发言人1',
      duration: '15:30',
      summary: '主要负责产品规划部分的汇报，详细介绍了用户调研结果和功能需求分析，提出了三个核心功能模块的设计方案。'
    },
    {
      id: '2', 
      name: '发言人2',
      duration: '12:45',
      summary: '从技术角度分析了实现方案的可行性，讨论了架构设计和技术选型，提出了性能优化建议。'
    },
    {
      id: '3',
      name: '发言人3', 
      duration: '8:20',
      summary: '负责市场分析和竞品对比，提供了用户画像和市场定位建议，强调了差异化竞争的重要性。'
    }
  ],
  todos: [
    '完成用户调研报告整理',
    '准备技术方案详细文档',
    '制定项目时间计划',
    '安排下次评审会议'
  ]
})

// 模拟转写数据
const mockTranscriptData = ref([
  {
    id: '1',
    speaker: '发言人1',
    startTime: '00:00',
    text: '大家好，今天我们主要讨论新产品的功能规划。根据最近的用户调研结果，我们发现用户对于语音识别功能有很强的需求。'
  },
  {
    id: '2', 
    speaker: '发言人2',
    startTime: '00:32',
    text: '从技术角度来看，语音识别的准确率是关键。我们需要考虑不同场景下的识别效果，包括噪音环境和多人对话。'
  },
  {
    id: '3',
    speaker: '发言人1',
    startTime: '01:15',
    text: '是的，这也是我们在用户访谈中发现的痛点。用户希望在会议场景下能够准确识别不同发言人的声音。'
  },
  {
    id: '4',
    speaker: '发言人3',
    startTime: '01:45',
    text: '市场上现有的产品在这方面还有改进空间。我们如果能在说话人识别上做得更好，会有很大的竞争优势。'
  }
])

// 音频控制相关方法
const togglePlay = () => {
  isPlaying.value = !isPlaying.value
  // 这里应该控制实际的音频播放
  ElMessage.info(isPlaying.value ? '开始播放' : '暂停播放')
}

const seekTo = (time: number) => {
  currentTime.value = time
  ElMessage.info(`跳转到 ${formatTime(time)}`)
}

const seekToSegment = (segment: any) => {
  activeSegment.value = segment.id
  // 解析时间字符串并跳转
  const timeMatch = segment.startTime.match(/(\d+):(\d+)/)
  if (timeMatch) {
    const minutes = parseInt(timeMatch[1])
    const seconds = parseInt(timeMatch[2])
    const totalSeconds = minutes * 60 + seconds
    seekTo(totalSeconds)
  }
}

const formatTime = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

// 生成相关功能
const generateSummary = () => {
  ElMessage.success('正在生成智能总结...')
  // 模拟生成过程
  setTimeout(() => {
    if (currentRecording.value) {
      currentRecording.value.hasSummary = true
    }
    ElMessage.success('智能总结生成完成')
  }, 2000)
}

const generateTranscript = () => {
  ElMessage.success('正在生成转写文本...')
  // 模拟转写过程
  setTimeout(() => {
    if (currentRecording.value) {
      currentRecording.value.hasTranscript = true
    }
    ElMessage.success('转写完成')
  }, 3000)
}

const addTodo = () => {
  // 这里应该打开添加待办的对话框
  ElMessage.info('添加待办功能待实现')
}

// 下载录音
const downloadRecording = (item: any) => {
  ElMessage.success(`下载录音: ${item.title}`)
}

// 重新处理
const reprocess = (item: any) => {
  ElMessage.success(`重新处理: ${item.title}`)
  item.status = 'processing'
}

// 删除录音
const deleteRecording = async (item: any) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除录音 "${item.title}" 吗？此操作不可撤销。`,
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )
    
    const index = recordings.value.findIndex(r => r.id === item.id)
    if (index > -1) {
      recordings.value.splice(index, 1)
      ElMessage.success('删除成功')
    }
  } catch {
    // 用户取消删除
  }
}


</script>

<style scoped>
.recordings-view {
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
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  flex: 1;
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

.header-actions {
  display: flex;
  gap: 12px;
}

/* 筛选区域 */
.filter-section {
  background: white;
  border-bottom: 1px solid #e4e7ed;
  padding: 20px 0;
}

.filter-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

/* 视图控制 */
.view-controls {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

/* 录音列表 */
.recordings-section {
  max-width: 1200px;
  margin: 24px auto;
  padding: 0 24px;
}

/* 卡片网格布局 */
.recordings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
  margin-top: 20px;
}

/* 录音卡片 */
.recording-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid #e4e7ed;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.04);
}

.recording-card:hover {
  border-color: #409eff;
  box-shadow: 0 8px 24px rgba(64, 158, 255, 0.12);
  transform: translateY(-2px);
}

/* 卡片头部 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.title-section {
  flex: 1;
  min-width: 0;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 4px 0;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recording-time {
  font-size: 12px;
  color: #909399;
}

.actions-section {
  display: flex;
  gap: 4px;
  margin-left: 12px;
}

.play-btn {
  color: #409eff !important;
}

/* 录音时长 */
.duration-info {
  margin-bottom: 12px;
}

.duration {
  font-size: 14px;
  color: #606266;
  font-weight: 500;
}

/* 关键词区域 */
.keywords-section {
  margin-bottom: 16px;
}

.keyword-tag {
  margin-right: 8px;
  margin-bottom: 6px;
}

/* 内容预览 */
.content-preview {
  margin-bottom: 16px;
  min-height: 60px;
}

.content-preview p {
  font-size: 14px;
  color: #606266;
  line-height: 1.6;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* 卡片底部 */
.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid #f0f2f5;
}

.footer-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #909399;
  font-size: 12px;
}

.meta-separator {
  color: #dcdfe6;
}

.status-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

/* 下拉菜单危险项 */
:deep(.danger-item) {
  color: #f56c6c;
}

:deep(.danger-item:hover) {
  background-color: #fef0f0;
  color: #f56c6c;
}

/* 空状态 */
.empty-state {
  max-width: 1200px;
  margin: 60px auto;
  padding: 0 24px;
  text-align: center;
}

/* 录音详情弹窗样式 */
:deep(.recording-details-dialog) {
  .el-dialog__body {
    padding: 0;
  }
}

.recording-details {
  min-height: 600px;
}

/* 详情头部 */
.details-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid #e4e7ed;
  background: #f8f9fa;
}

.recording-meta-info {
  display: flex;
  gap: 24px;
  flex-wrap: wrap;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #606266;
  font-size: 14px;
}

/* 标签页样式 */
.details-tabs {
  margin: 0;
}

:deep(.details-tabs .el-tabs__header) {
  margin: 0;
  background: white;
  border-bottom: 1px solid #e4e7ed;
}

:deep(.details-tabs .el-tabs__nav-wrap) {
  padding: 0 24px;
}

.tab-content {
  padding: 24px;
  min-height: 500px;
}

/* 智能总结样式 */
.summary-section {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.summary-block {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 20px;
}

.summary-block h3 {
  margin: 0 0 16px 0;
  color: #303133;
  font-size: 16px;
  font-weight: 600;
}

.keywords-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.keyword-tag {
  margin: 0;
}

.summary-text {
  color: #606266;
  line-height: 1.6;
  font-size: 14px;
}

.speaker-summaries {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.speaker-summary {
  background: white;
  border-radius: 8px;
  padding: 16px;
  border: 1px solid #e4e7ed;
}

.speaker-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.speaker-name {
  font-weight: 500;
  color: #303133;
}

.speaker-time {
  color: #909399;
  font-size: 12px;
  margin-left: auto;
}

.speaker-content {
  color: #606266;
  line-height: 1.6;
  font-size: 14px;
}

.todos-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.todo-item {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #606266;
  font-size: 14px;
}

.no-summary, .no-transcript, .no-todos {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}

/* 音频控制样式 */
.audio-controls {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 20px;
}

.time-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #606266;
  font-size: 14px;
}

/* 转写文本样式 */
.transcript-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.transcript-segment {
  background: white;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.3s;
}

.transcript-segment:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

.transcript-segment.active {
  border-color: #409eff;
  background: #ecf5ff;
}

.segment-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.segment-time {
  color: #909399;
  font-size: 12px;
  margin-left: auto;
}

.segment-text {
  color: #303133;
  line-height: 1.6;
  font-size: 14px;
}

/* 待办事项样式 */
.todos-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.todos-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.todos-header h3 {
  margin: 0;
  color: #303133;
  font-size: 16px;
  font-weight: 600;
}

.todo-item-detailed {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: white;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
}

.delete-todo {
  color: #f56c6c;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }

  .filter-content .el-row {
    flex-direction: column;
    gap: 12px;
  }

  .filter-content .el-col {
    width: 100% !important;
  }

  .recordings-section {
    padding: 0 16px;
  }

  /* 卡片布局响应式 */
  .recordings-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .recording-card {
    padding: 16px;
  }

  .card-header {
    align-items: center;
  }

  .actions-section {
    margin-left: 8px;
  }

  .card-title {
    font-size: 15px;
  }

  .content-preview {
    min-height: 50px;
  }

  .content-preview p {
    -webkit-line-clamp: 2;
  }

  .card-footer {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }

  .status-badges {
    justify-content: flex-start;
  }

  .details-header {
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }

  .recording-meta-info {
    justify-content: center;
  }

  .tab-content {
    padding: 16px;
  }

  .audio-controls {
    flex-direction: column;
    gap: 12px;
  }

  .transcript-segment {
    padding: 12px;
  }
}

@media (max-width: 576px) {
  .recordings-grid {
    gap: 12px;
  }

  .recording-card {
    padding: 12px;
    border-radius: 8px;
  }

  .card-title {
    font-size: 14px;
  }

  .keywords-section .keyword-tag {
    margin-right: 4px;
    margin-bottom: 4px;
  }
}
</style> 