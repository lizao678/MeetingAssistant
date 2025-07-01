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
            <el-space>
              <el-button 
                :disabled="selectedRecordings.length === 0"
                @click="batchDelete"
              >
                批量删除 ({{ selectedRecordings.length }})
              </el-button>
            </el-space>
          </el-col>
        </el-row>
      </div>
    </div>

    <!-- 录音列表 -->
    <div class="recordings-section">
      <el-table
        :data="filteredRecordings"
        @selection-change="handleSelectionChange"
        class="recordings-table"
        empty-text="暂无录音记录"
      >
        <el-table-column type="selection" width="55" />
        
        <el-table-column label="录音信息" min-width="300">
          <template #default="{ row }">
            <div class="recording-info">
              <div class="recording-header">
                <h3 class="recording-title">{{ row.title }}</h3>
                <el-tag
                  :type="getStatusType(row.status)"
                  size="small"
                  class="status-tag"
                >
                  {{ getStatusText(row.status) }}
                </el-tag>
              </div>
              <p class="recording-description">{{ row.description }}</p>
              <div class="recording-meta">
                <span><el-icon><Clock /></el-icon> {{ row.duration }}</span>
                <span><el-icon><Files /></el-icon> {{ row.fileSize }}</span>
                <span><el-icon><User /></el-icon> {{ row.speakerCount }}人</span>
                <span>{{ row.language }}</span>
              </div>
              <div v-if="row.tags.length > 0" class="recording-tags">
                <el-tag
                  v-for="tag in row.tags"
                  :key="tag"
                  size="small"
                  type="info"
                  effect="plain"
                >
                  {{ tag }}
                </el-tag>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            <div class="time-info">
              <div>{{ row.createTime }}</div>
              <div class="update-time">更新: {{ row.updateTime }}</div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <div class="status-info">
              <el-tag :type="getStatusType(row.status)" size="small">
                {{ getStatusText(row.status) }}
              </el-tag>
              <div class="feature-badges">
                <el-badge v-if="row.hasTranscript" value="转写" type="success" />
                <el-badge v-if="row.hasSummary" value="总结" type="primary" />
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip content="播放录音" placement="top">
                <el-button
                  text
                  size="small"
                  :icon="'VideoPlay'"
                  @click="playRecording(row)"
                />
              </el-tooltip>
              
              <el-tooltip content="查看转写" placement="top">
                <el-button
                  text
                  size="small"
                  :icon="'Document'"
                  :disabled="!row.hasTranscript"
                  @click="viewTranscript(row)"
                />
              </el-tooltip>
              
              <el-tooltip content="智能总结" placement="top">
                <el-button
                  text
                  size="small"
                  :icon="'ChatDotSquare'"
                  :disabled="!row.hasSummary"
                  @click="viewSummary(row)"
                />
              </el-tooltip>

              <el-dropdown trigger="click">
                <el-button text size="small" :icon="'More'" />
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item :icon="'Download'" @click="downloadRecording(row)">
                      下载录音
                    </el-dropdown-item>
                    <el-dropdown-item 
                      v-if="row.status === 'failed'" 
                      :icon="'Refresh'" 
                      @click="reprocess(row)"
                    >
                      重新处理
                    </el-dropdown-item>
                    <el-dropdown-item 
                      :icon="'Delete'" 
                      @click="deleteRecording(row)"
                      class="danger-item"
                    >
                      删除录音
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </template>
        </el-table-column>
      </el-table>
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
    hasSummary: true
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
    hasSummary: true
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
    hasSummary: false
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
    hasSummary: false
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

// 查看智能总结
const viewSummary = (item: any) => {
  router.push(`/summary/${item.id}`)
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

// 批量操作
const selectedRecordings = ref<string[]>([])
const handleSelectionChange = (selection: any[]) => {
  selectedRecordings.value = selection.map(item => item.id)
}

// 批量删除
const batchDelete = async () => {
  if (selectedRecordings.value.length === 0) {
    ElMessage.warning('请选择要删除的录音')
    return
  }
  
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedRecordings.value.length} 个录音吗？此操作不可撤销。`,
      '批量删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--danger'
      }
    )
    
    recordings.value = recordings.value.filter(r => !selectedRecordings.value.includes(r.id))
    selectedRecordings.value = []
    ElMessage.success('批量删除成功')
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

/* 录音列表 */
.recordings-section {
  max-width: 1200px;
  margin: 24px auto;
  padding: 0 24px;
}

.recordings-table {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

/* 录音信息 */
.recording-info {
  padding: 4px 0;
}

.recording-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.recording-title {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
  margin: 0;
  flex: 1;
}

.status-tag {
  flex-shrink: 0;
}

.recording-description {
  color: #606266;
  margin: 0 0 12px 0;
  font-size: 14px;
  line-height: 1.4;
}

.recording-meta {
  display: flex;
  gap: 16px;
  margin-bottom: 8px;
  font-size: 13px;
  color: #909399;
}

.recording-meta span {
  display: flex;
  align-items: center;
  gap: 4px;
}

.recording-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

/* 时间信息 */
.time-info {
  font-size: 14px;
  color: #303133;
}

.update-time {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

/* 状态信息 */
.status-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.feature-badges {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

/* 操作按钮 */
.action-buttons {
  display: flex;
  gap: 4px;
  align-items: center;
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

  .recording-meta {
    flex-direction: column;
    gap: 8px;
  }

  .action-buttons {
    flex-wrap: wrap;
  }
}
</style> 