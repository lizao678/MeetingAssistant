<template>
  <div class="search-filter">
    <!-- 搜索输入框 -->
    <div class="search-section">
      <el-input
        v-model="searchQuery"
        placeholder="搜索录音标题、摘要内容或关键词..."
        :prefix-icon="Search"
        clearable
        size="large"
        class="search-input"
        @input="handleSearchInput"
        @clear="handleSearchClear"
      >
        <template #append>
          <el-button :icon="Search" @click="handleSearch" />
        </template>
      </el-input>
    </div>

    <!-- 筛选条件 -->
    <div class="filter-section">
      <el-row :gutter="16" align="middle">
        <!-- 状态筛选 -->
        <el-col :span="6">
          <el-select
            v-model="statusFilter"
            placeholder="状态筛选"
            clearable
            size="default"
            @change="handleStatusChange"
          >
            <el-option
              v-for="option in statusOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            >
              <div class="status-option">
                <el-tag 
                  :type="getStatusTagType(option.value)" 
                  size="small" 
                  effect="plain"
                >
                  {{ option.label }}
                </el-tag>
              </div>
            </el-option>
          </el-select>
        </el-col>

        <!-- 发言人数筛选 -->
        <el-col :span="6">
          <el-select
            v-model="speakerCountFilter"
            placeholder="发言人数"
            clearable
            size="default"
            @change="handleSpeakerCountChange"
          >
            <el-option label="1人" value="1" />
            <el-option label="2人" value="2" />
            <el-option label="3-5人" value="3-5" />
            <el-option label="6人以上" value="6+" />
          </el-select>
        </el-col>

        <!-- 时间范围筛选 -->
        <el-col :span="8">
          <el-date-picker
            v-model="dateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            size="default"
            :shortcuts="dateShortcuts"
            @change="handleDateRangeChange"
          />
        </el-col>

        <!-- 排序选择 -->
        <el-col :span="4">
          <el-select
            v-model="sortOption"
            placeholder="排序方式"
            size="default"
            @change="handleSortChange"
          >
            <el-option
              v-for="option in sortOptions"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            >
              <div class="sort-option">
                <el-icon>
                  <component :is="option.icon" />
                </el-icon>
                {{ option.label }}
              </div>
            </el-option>
          </el-select>
        </el-col>
      </el-row>
    </div>

    <!-- 高级搜索切换 -->
    <div class="advanced-toggle">
      <el-button 
        text 
        size="small" 
        :icon="advancedVisible ? ArrowUp : ArrowDown"
        @click="toggleAdvanced"
      >
        {{ advancedVisible ? '收起' : '高级筛选' }}
      </el-button>
    </div>

    <!-- 高级筛选选项 -->
    <el-collapse-transition>
      <div v-show="advancedVisible" class="advanced-section">
        <el-row :gutter="16">
          <!-- 时长筛选 -->
          <el-col :span="8">
            <div class="filter-group">
              <label class="filter-label">录音时长</label>
              <el-slider
                v-model="durationRange"
                range
                :min="0"
                :max="180"
                :step="5"
                :format-tooltip="formatDurationTooltip"
                @change="handleDurationChange"
              />
              <div class="range-labels">
                <span>{{ formatDuration(durationRange[0]) }}</span>
                <span>{{ formatDuration(durationRange[1]) }}</span>
              </div>
            </div>
          </el-col>

          <!-- 文件大小筛选 -->
          <el-col :span="8">
            <div class="filter-group">
              <label class="filter-label">文件大小</label>
              <el-select
                v-model="fileSizeFilter"
                placeholder="选择大小范围"
                clearable
                @change="handleFileSizeChange"
              >
                <el-option label="小于 50MB" value="<50" />
                <el-option label="50MB - 100MB" value="50-100" />
                <el-option label="100MB - 200MB" value="100-200" />
                <el-option label="大于 200MB" value=">200" />
              </el-select>
            </div>
          </el-col>

          <!-- 语言筛选 -->
          <el-col :span="8">
            <div class="filter-group">
              <label class="filter-label">语言</label>
              <el-select
                v-model="languageFilter"
                placeholder="选择语言"
                clearable
                @change="handleLanguageChange"
              >
                <el-option label="中文" value="中文" />
                <el-option label="English" value="English" />
                <el-option label="日本語" value="日本語" />
                <el-option label="한국어" value="한국어" />
              </el-select>
            </div>
          </el-col>
        </el-row>

        <!-- 清除所有筛选 -->
        <div class="clear-section">
          <el-button 
            size="small" 
            :icon="RefreshLeft"
            @click="clearAllFilters"
          >
            清除所有筛选条件
          </el-button>
        </div>
      </div>
    </el-collapse-transition>

    <!-- 活跃的筛选标签 -->
    <div v-if="activeFilters.length > 0" class="active-filters">
      <div class="filter-tags">
        <el-tag
          v-for="filter in activeFilters"
          :key="filter.key"
          type="primary"
          effect="plain"
          closable
          @close="removeFilter(filter.key)"
        >
          {{ filter.label }}
        </el-tag>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { 
  Search, ArrowDown, ArrowUp, RefreshLeft, Clock, 
  Calendar, Sort, Star 
} from '@element-plus/icons-vue'
// 简单的防抖函数实现
function useDebounceFn(fn: Function, delay: number) {
  let timeoutId: number | null = null
  return (...args: any[]) => {
    if (timeoutId) clearTimeout(timeoutId)
    timeoutId = setTimeout(() => fn(...args), delay)
  }
}

// Props 和 Emits
interface FilterParams {
  search: string
  status: string
  speakerCount: string
  dateRange: [Date, Date] | null
  sort: string
  duration: [number, number]
  fileSize: string
  language: string
}

const emit = defineEmits<{
  'filter-change': [params: FilterParams]
  'search': [query: string]
}>()

// 搜索相关
const searchQuery = ref('')
const advancedVisible = ref(false)

// 基础筛选
const statusFilter = ref('')
const speakerCountFilter = ref('')
const dateRange = ref<[Date, Date] | null>(null)
const sortOption = ref('createTime-desc')

// 高级筛选
const durationRange = ref<[number, number]>([0, 180]) // 分钟
const fileSizeFilter = ref('')
const languageFilter = ref('')

// 状态选项
const statusOptions = [
  { label: '已完成', value: 'completed' },
  { label: '处理中', value: 'processing' },
  { label: '处理失败', value: 'failed' }
]

// 排序选项
const sortOptions = [
  { label: '创建时间（最新）', value: 'createTime-desc', icon: Calendar },
  { label: '创建时间（最早）', value: 'createTime-asc', icon: Calendar },
  { label: '时长（最长）', value: 'duration-desc', icon: Clock },
  { label: '时长（最短）', value: 'duration-asc', icon: Clock },
  { label: '文件大小', value: 'fileSize-desc', icon: Sort },
  { label: '质量评分', value: 'quality-desc', icon: Star }
]

// 日期快捷选项
const dateShortcuts = [
  {
    text: '今天',
    value: () => {
      const start = new Date()
      start.setHours(0, 0, 0, 0)
      const end = new Date()
      end.setHours(23, 59, 59, 999)
      return [start, end]
    }
  },
  {
    text: '昨天',
    value: () => {
      const start = new Date()
      start.setDate(start.getDate() - 1)
      start.setHours(0, 0, 0, 0)
      const end = new Date()
      end.setDate(end.getDate() - 1)
      end.setHours(23, 59, 59, 999)
      return [start, end]
    }
  },
  {
    text: '最近3天',
    value: () => {
      const start = new Date()
      start.setDate(start.getDate() - 2)
      start.setHours(0, 0, 0, 0)
      const end = new Date()
      end.setHours(23, 59, 59, 999)
      return [start, end]
    }
  },
  {
    text: '本周',
    value: () => {
      const start = new Date()
      const day = start.getDay()
      const diff = start.getDate() - day + (day === 0 ? -6 : 1)
      start.setDate(diff)
      start.setHours(0, 0, 0, 0)
      const end = new Date()
      end.setHours(23, 59, 59, 999)
      return [start, end]
    }
  },
  {
    text: '本月',
    value: () => {
      const start = new Date()
      start.setDate(1)
      start.setHours(0, 0, 0, 0)
      const end = new Date()
      end.setHours(23, 59, 59, 999)
      return [start, end]
    }
  }
]

// 活跃的筛选条件
const activeFilters = computed(() => {
  const filters = []
  
  if (statusFilter.value) {
    const option = statusOptions.find(opt => opt.value === statusFilter.value)
    filters.push({ key: 'status', label: `状态: ${option?.label}` })
  }
  
  if (speakerCountFilter.value) {
    filters.push({ key: 'speakerCount', label: `发言人: ${speakerCountFilter.value}` })
  }
  
  if (dateRange.value) {
    const [start, end] = dateRange.value
    filters.push({ 
      key: 'dateRange', 
      label: `时间: ${start.toLocaleDateString()} - ${end.toLocaleDateString()}` 
    })
  }
  
  if (fileSizeFilter.value) {
    filters.push({ key: 'fileSize', label: `大小: ${fileSizeFilter.value}MB` })
  }
  
  if (languageFilter.value) {
    filters.push({ key: 'language', label: `语言: ${languageFilter.value}` })
  }
  
  if (durationRange.value[0] > 0 || durationRange.value[1] < 180) {
    filters.push({ 
      key: 'duration', 
      label: `时长: ${formatDuration(durationRange.value[0])} - ${formatDuration(durationRange.value[1])}` 
    })
  }
  
  return filters
})

// 防抖搜索
const debouncedSearch = useDebounceFn((query: string) => {
  emit('search', query)
  emitFilterChange()
}, 300)

// 事件处理
const handleSearchInput = () => {
  debouncedSearch(searchQuery.value)
}

const handleSearchClear = () => {
  searchQuery.value = ''
  emit('search', '')
  emitFilterChange()
}

const handleSearch = () => {
  emit('search', searchQuery.value)
  emitFilterChange()
}

const toggleAdvanced = () => {
  advancedVisible.value = !advancedVisible.value
}

// 筛选变化处理
const handleStatusChange = () => emitFilterChange()
const handleSpeakerCountChange = () => emitFilterChange()
const handleDateRangeChange = () => emitFilterChange()
const handleSortChange = () => emitFilterChange()
const handleDurationChange = () => emitFilterChange()
const handleFileSizeChange = () => emitFilterChange()
const handleLanguageChange = () => emitFilterChange()

// 发送筛选参数
const emitFilterChange = () => {
  const params: FilterParams = {
    search: searchQuery.value,
    status: statusFilter.value,
    speakerCount: speakerCountFilter.value,
    dateRange: dateRange.value,
    sort: sortOption.value,
    duration: durationRange.value,
    fileSize: fileSizeFilter.value,
    language: languageFilter.value
  }
  emit('filter-change', params)
}

// 移除单个筛选
const removeFilter = (key: string) => {
  switch (key) {
    case 'status':
      statusFilter.value = ''
      break
    case 'speakerCount':
      speakerCountFilter.value = ''
      break
    case 'dateRange':
      dateRange.value = null
      break
    case 'fileSize':
      fileSizeFilter.value = ''
      break
    case 'language':
      languageFilter.value = ''
      break
    case 'duration':
      durationRange.value = [0, 180]
      break
  }
  emitFilterChange()
}

// 清除所有筛选
const clearAllFilters = () => {
  searchQuery.value = ''
  statusFilter.value = ''
  speakerCountFilter.value = ''
  dateRange.value = null
  sortOption.value = 'createTime-desc'
  durationRange.value = [0, 180]
  fileSizeFilter.value = ''
  languageFilter.value = ''
  emitFilterChange()
}

// 工具函数
const getStatusTagType = (status: string) => {
  switch (status) {
    case 'completed': return 'success'
    case 'processing': return 'warning'
    case 'failed': return 'danger'
    default: return 'info'
  }
}

const formatDuration = (minutes: number) => {
  if (minutes === 0) return '0分'
  if (minutes >= 60) {
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    return mins > 0 ? `${hours}时${mins}分` : `${hours}时`
  }
  return `${minutes}分`
}

const formatDurationTooltip = (value: number) => {
  return formatDuration(value)
}

// 监听筛选条件变化
watch([statusFilter, speakerCountFilter, dateRange, sortOption], () => {
  emitFilterChange()
}, { deep: true })
</script>

<style scoped>
.search-filter {
  background: white;
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

/* 搜索区域 */
.search-section {
  margin-bottom: 16px;
}

.search-input {
  max-width: 600px;
}

.search-input :deep(.el-input__wrapper) {
  border-radius: 24px;
  border: 2px solid #e4e7ed;
  transition: all 0.3s;
}

.search-input :deep(.el-input__wrapper:hover) {
  border-color: #409eff;
}

.search-input :deep(.el-input__wrapper.is-focus) {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.1);
}

/* 筛选区域 */
.filter-section {
  margin-bottom: 12px;
}

.status-option,
.sort-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 高级筛选切换 */
.advanced-toggle {
  text-align: center;
  margin-bottom: 16px;
}

/* 高级筛选区域 */
.advanced-section {
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  margin-bottom: 16px;
}

.filter-group {
  margin-bottom: 16px;
}

.filter-label {
  display: block;
  font-size: 13px;
  color: #606266;
  margin-bottom: 8px;
  font-weight: 500;
}

.range-labels {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.clear-section {
  text-align: center;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #e4e7ed;
}

/* 活跃筛选标签 */
.active-filters {
  padding-top: 16px;
  border-top: 1px solid #e4e7ed;
}

.filter-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.filter-tags .el-tag {
  border-radius: 20px;
  padding: 4px 12px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .search-filter {
    padding: 16px;
  }
  
  .filter-section .el-col {
    margin-bottom: 12px;
  }
  
  .advanced-section .el-col {
    margin-bottom: 16px;
  }
}
</style> 