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
          <p class="page-subtitle">
            共 {{ totalCount }} 条录音记录
            <span v-if="filteredCount !== totalCount">
              ，筛选后 {{ filteredCount }} 条
            </span>
          </p>
        </div>
        <div class="header-actions">
          <el-button 
            v-if="recordings.length > 2"
            type="warning" 
            :icon="Delete" 
            @click="handleBatchCleanup"
            size="large"
          >
            清理记录
          </el-button>
          <el-button 
            type="primary" 
            :icon="Plus" 
            @click="router.push('/realtime')"
            size="large"
          >
            新建录音
          </el-button>
          <el-button 
            :icon="Upload" 
            @click="router.push('/upload')"
            size="large"
          >
            上传文件
          </el-button>
        </div>
      </div>
    </div>

    <!-- 搜索筛选组件 -->
    <div class="filter-container">
      <SearchFilter 
        @filter-change="handleFilterChange"
        @search="handleSearch"
      />
    </div>

    <!-- 录音列表容器 -->
    <div class="recordings-container">
      <!-- 加载状态 -->
      <div v-if="loading" class="loading-container">
        <el-skeleton 
          :rows="3" 
          animated 
          :loading="loading"
          class="recording-skeleton"
        >
          <template #template>
            <div class="skeleton-card">
              <el-skeleton-item variant="h3" />
              <el-skeleton-item variant="text" />
              <el-skeleton-item variant="text" />
              <el-skeleton-item variant="button" />
            </div>
                </template>
        </el-skeleton>
          </div>

      <!-- 录音卡片网格 -->
      <div v-else-if="recordings.length > 0" class="recordings-grid">
        <RecordingCard
          v-for="recording in recordings"
          :key="recording.id"
          :recording="recording"
          @click="handleCardClick"
          @play="handlePlay"
          @view="handleViewDetails"
          @download="handleDownload"
          @edit="handleEdit"
          @reprocess="handleReprocess"
          @regenerate-summary="handleRegenerateSummary"
          @delete="handleDelete"
        />
          </div>

      <!-- 空状态 -->
      <div v-else class="empty-container">
        <el-empty 
          :description="hasActiveFilters ? '没有符合条件的录音记录' : '还没有录音记录'"
          :image-size="120"
        >
          <el-button 
            v-if="hasActiveFilters"
                type="primary"
            @click="clearFilters"
          >
          清除筛选条件
        </el-button>
          <el-button 
            v-else
                      type="primary"
            :icon="Plus"
            @click="router.push('/realtime')"
            size="large"
          >
            立即开始录音
                  </el-button>
                </el-empty>
              </div>

      <!-- 分页组件 -->
      <div v-if="recordings.length > 0" class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[12, 24, 48, 96]"
          :total="filteredCount"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handlePageSizeChange"
          @current-change="handlePageChange"
        />
                  </div>
                </div>

    <!-- 编辑标题对话框 -->
    <el-dialog 
      v-model="editDialogVisible" 
      title="编辑录音标题" 
      width="400px"
    >
      <el-form>
        <el-form-item label="录音标题">
          <el-input 
            v-model="editTitle" 
            placeholder="请输入录音标题"
            maxlength="100"
            show-word-limit
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="confirmEdit" :loading="updating">
            确定
                  </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import { Folder, Plus, Upload, Delete } from '@element-plus/icons-vue'

import RecordingCard from '@/components/RecordingCard.vue'
import SearchFilter from '@/components/SearchFilter.vue'
import recordingService from '@/services/recordingService'
import type { RecordingDetail } from '@/types/audio'

const router = useRouter()

// 数据状态
const recordings = ref<RecordingDetail[]>([])
const loading = ref(false)
const totalCount = ref(0)
const filteredCount = ref(0)
const currentPage = ref(1)
const pageSize = ref(12)

// 筛选状态
const currentFilters = ref<any>({})
const searchQuery = ref('')
const hasActiveFilters = computed(() => {
  return searchQuery.value || 
         currentFilters.value.status || 
         currentFilters.value.speakerCount ||
         currentFilters.value.dateRange ||
         currentFilters.value.fileSize ||
         currentFilters.value.language ||
         (currentFilters.value.duration && 
          (currentFilters.value.duration[0] > 0 || currentFilters.value.duration[1] < 180))
})

// 编辑对话框
const editDialogVisible = ref(false)
const editTitle = ref('')
const editingRecording = ref<RecordingDetail | null>(null)
const updating = ref(false)

// 获取录音列表
const fetchRecordings = async () => {
  try {
    loading.value = true
    
    // 构建查询参数
    const params = {
      page: currentPage.value,
      limit: pageSize.value,
      search: searchQuery.value,
      ...currentFilters.value
    }
    
    const response = await recordingService.getRecordings(params)
    
    // 转换API数据格式为组件需要的格式
    recordings.value = response.data.recordings.map(convertRecordingFormat)
    totalCount.value = response.data.total
    filteredCount.value = response.data.total
    
  } catch (error) {
    console.error('获取录音列表失败:', error)
    ElMessage.error('获取录音列表失败')
  } finally {
    loading.value = false
  }
}

// 转换录音数据格式
const convertRecordingFormat = (recording: any): RecordingDetail => {
  return {
    id: recording.id,
    title: recording.title || `录音 ${recording.id}`,
    duration: formatDuration(recording.duration),
    fileSize: recording.fileSize || 0,
    createTime: recording.createTime,
    updateTime: recording.updateTime,
    status: recording.status,
    language: recording.language || '中文',
    speakerCount: recording.speakerCount || 1,
    summary: recording.summary ? {
      content: recording.summary.content,
      quality: recording.summary.quality,
      wordCount: recording.summary.wordCount,
      keyPoints: recording.summary.keyPoints || []
    } : undefined,
    keywords: recording.keywords || [],
    segments: recording.segments || []
  }
}

// 格式化时长
const formatDuration = (seconds: number): string => {
  if (!seconds) return '00:00'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

// 事件处理
const handleFilterChange = (filters: any) => {
  currentFilters.value = filters
  currentPage.value = 1 // 重置到第一页
  fetchRecordings()
}

const handleSearch = (query: string) => {
  searchQuery.value = query
  currentPage.value = 1
  fetchRecordings()
}

const clearFilters = () => {
  currentFilters.value = {}
  searchQuery.value = ''
  currentPage.value = 1
  fetchRecordings()
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchRecordings()
}

const handlePageSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  fetchRecordings()
}

// 录音卡片事件处理
const handleCardClick = (recording: RecordingDetail) => {
  router.push(`/recording/${recording.id}`)
}

const handlePlay = (recording: RecordingDetail) => {
  if (recording.status !== 'completed') {
    ElMessage.warning('录音还在处理中，暂无法播放')
    return
  }
  router.push(`/recording/${recording.id}`)
}

const handleViewDetails = (recording: RecordingDetail) => {
  router.push(`/recording/${recording.id}`)
}

const handleDownload = async (recording: RecordingDetail) => {
  if (recording.status !== 'completed') {
    ElMessage.warning('录音还在处理中，暂无法下载')
    return
  }
  
  try {
    const loadingInstance = ElLoading.service({
      lock: true,
      text: '正在下载录音文件...'
    })
    
    await recordingService.downloadRecording(recording.id)
    ElMessage.success('下载成功')
    
    loadingInstance.close()
  } catch (error) {
    console.error('下载失败:', error)
    ElMessage.error('下载失败')
  }
}

const handleEdit = (recording: RecordingDetail) => {
  editingRecording.value = recording
  editTitle.value = recording.title
  editDialogVisible.value = true
}

const confirmEdit = async () => {
  if (!editingRecording.value || !editTitle.value.trim()) {
    ElMessage.warning('请输入录音标题')
    return
  }
  
  try {
    updating.value = true
    
    // 更新本地数据
    const index = recordings.value.findIndex(r => r.id === editingRecording.value!.id)
    if (index > -1) {
      recordings.value[index].title = editTitle.value
    }
    
    editDialogVisible.value = false
    ElMessage.success('标题更新成功')
    
  } catch (error) {
    console.error('更新标题失败:', error)
    ElMessage.error('更新标题失败')
  } finally {
    updating.value = false
  }
}

const handleReprocess = async (recording: RecordingDetail) => {
  try {
    await ElMessageBox.confirm(
      '重新处理将使用离线高精度模型重新识别音频，可能需要一些时间。是否继续？',
      '确认重新处理',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'info'
      }
    )
    
    const loadingInstance = ElLoading.service({
      lock: true,
      text: '正在启动离线重新处理...'
    })
    
    await recordingService.offlineReprocessRecording(recording.id)
    
    // 更新状态为处理中
    const index = recordings.value.findIndex(r => r.id === recording.id)
    if (index > -1) {
      recordings.value[index].status = 'processing'
    }
    
    ElMessage.success('已开始重新处理，请稍后查看结果')
    loadingInstance.close()
    
  } catch (error) {
    if (error !== 'cancel') {
      console.error('重新处理失败:', error)
      ElMessage.error('重新处理失败')
    }
  }
}

const handleRegenerateSummary = async (recording: RecordingDetail) => {
  try {
    await ElMessageBox.confirm(
      '重新生成摘要将覆盖当前的AI摘要内容。是否继续？',
      '确认重新生成',
      {
        confirmButtonText: '确认',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    const loadingInstance = ElLoading.service({
      lock: true,
      text: '正在重新生成摘要...'
    })
    
    await recordingService.regenerateSummary(recording.id)
    
    // 刷新数据
    await fetchRecordings()
    
    ElMessage.success('摘要重新生成成功')
    loadingInstance.close()
    
  } catch (error) {
    if (error !== 'cancel') {
      console.error('重新生成摘要失败:', error)
      ElMessage.error('重新生成摘要失败')
    }
  }
}

const handleDelete = async (recording: RecordingDetail) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除录音 "${recording.title}" 吗？此操作不可撤销。`,
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'error',
        confirmButtonClass: 'el-button--danger'
      }
    )
    
    const loadingInstance = ElLoading.service({
      lock: true,
      text: '正在删除...'
    })
    
    await recordingService.deleteRecording(recording.id)
    
    // 从列表中移除
    const index = recordings.value.findIndex(r => r.id === recording.id)
    if (index > -1) {
      recordings.value.splice(index, 1)
      totalCount.value--
      filteredCount.value--
    }
    
    ElMessage.success('删除成功')
    loadingInstance.close()
    
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

// 批量清理 - 保留最新2条记录
const handleBatchCleanup = async () => {
  try {
    const totalRecordings = recordings.value.length
    if (totalRecordings <= 2) {
      ElMessage.info('记录数量不足，无需清理')
      return
    }
    
    const keepCount = 2
    const deleteCount = totalRecordings - keepCount
    
    await ElMessageBox.confirm(
      `此操作将保留最新的 ${keepCount} 条记录，删除其余 ${deleteCount} 条记录。删除的记录不可恢复，确定继续吗？`,
      '批量清理录音记录',
      {
        confirmButtonText: '确认清理',
        cancelButtonText: '取消',
        type: 'warning',
        confirmButtonClass: 'el-button--warning',
        dangerouslyUseHTMLString: true
      }
    )
    
    const loadingInstance = ElLoading.service({
      lock: true,
      text: `正在清理 ${deleteCount} 条记录...`
    })
    
    // 按创建时间排序，最新的在前面
    const sortedRecordings = [...recordings.value].sort((a, b) => 
      new Date(b.createTime).getTime() - new Date(a.createTime).getTime()
    )
    
    // 获取需要删除的记录
    const recordingsToDelete = sortedRecordings.slice(keepCount)
    
    let successCount = 0
    let failCount = 0
    
    // 批量删除
    for (const recording of recordingsToDelete) {
      try {
        await recordingService.deleteRecording(recording.id)
        
        // 从列表中移除
        const index = recordings.value.findIndex(r => r.id === recording.id)
        if (index > -1) {
          recordings.value.splice(index, 1)
          totalCount.value--
          filteredCount.value--
        }
        successCount++
      } catch (error) {
        console.error(`删除录音 ${recording.id} 失败:`, error)
        failCount++
      }
    }
    
    loadingInstance.close()
    
    if (failCount === 0) {
      ElMessage.success(`清理完成！成功删除 ${successCount} 条记录，保留 ${keepCount} 条最新记录`)
    } else {
      ElMessage.warning(`清理部分完成！成功删除 ${successCount} 条，失败 ${failCount} 条`)
    }
    
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量清理失败:', error)
      ElMessage.error('批量清理失败')
    }
  }
}

// 页面初始化
onMounted(() => {
  fetchRecordings()
})
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

/* 筛选容器 */
.filter-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
}

/* 录音列表容器 */
.recordings-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
  min-height: 400px;
}

/* 加载状态 */
.loading-container {
  padding: 20px 0;
}

.recording-skeleton {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
}

.skeleton-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  border: 1px solid #e4e7ed;
}

/* 录音网格 */
.recordings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 20px;
  padding: 20px 0;
}

/* 空状态 */
.empty-container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  padding: 60px 24px;
}

/* 分页 */
.pagination-container {
  display: flex;
  justify-content: center;
  padding: 40px 0;
  border-top: 1px solid #e4e7ed;
  margin-top: 20px;
}

/* 对话框 */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    align-items: stretch;
    gap: 16px;
  }
  
  .header-actions {
    justify-content: center;
  }
  
  .recordings-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .recording-skeleton {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 480px) {
  .page-header {
    padding: 16px 0;
  }
  
  .header-content,
  .filter-container,
  .recordings-container {
    padding: 0 16px;
  }
  
  .page-title {
    font-size: 24px;
  }
  
  .header-actions {
    flex-direction: column;
  }
}
</style> 