<template>
  <el-dialog
    v-model="visible"
    title="设置发言人"
    width="500px"
    :before-close="handleClose"
    class="speaker-setting-dialog"
  >
    <div class="dialog-content">
      <!-- 发言人名称输入 -->
      <div class="setting-section">
        <el-input
          v-model="speakerName"
          placeholder="发言人 1"
          size="large"
          class="speaker-input"
        />
      </div>

      <!-- 设置范围选择 -->
      <div class="setting-section">
        <div class="range-selector">
          <el-button
            :type="settingRange === 'single' ? 'primary' : 'default'"
            @click="settingRange = 'single'"
            class="range-button"
          >
            单个
          </el-button>
          <el-button
            :type="settingRange === 'global' ? 'primary' : 'default'"
            @click="settingRange = 'global'"
            class="range-button"
          >
            全局
          </el-button>
        </div>
      </div>

      <!-- 分类选择 -->
      <div class="setting-section">
        <el-tabs v-model="activeTab" class="speaker-tabs">
          <el-tab-pane label="当前录音发言人" name="current">
            <div class="speaker-list">
              <div
                v-for="speaker in currentSpeakers"
                :key="speaker.id"
                class="speaker-item"
                :class="{ active: selectedSpeaker?.id === speaker.id }"
                @click="selectSpeaker(speaker)"
              >
                <el-avatar
                  :size="40"
                  :style="{ backgroundColor: speaker.color }"
                >
                  {{ getCurrentSpeakerAvatarText(speaker) }}
                </el-avatar>
                <div class="speaker-info">
                  <div class="speaker-name">{{ speaker.name }}</div>
                  <div class="speaker-stats">{{ speaker.segmentCount }}段发言</div>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="常用发言人" name="frequent">
            <div class="speaker-list">
              <div
                v-for="speaker in speakerStore.frequentSpeakers"
                :key="speaker.id"
                class="speaker-item"
                :class="{ active: selectedSpeaker?.id === speaker.id }"
                @click="selectSpeaker(speaker)"
              >
                <el-avatar
                  :size="40"
                  :style="{ backgroundColor: speaker.color }"
                >
                  {{ speaker.name.charAt(0) }}
                </el-avatar>
                <div class="speaker-info">
                  <div class="speaker-name">{{ speaker.name }}</div>
                  <div class="speaker-stats">使用{{ speaker.useCount }}次</div>
                </div>
                <el-button
                  size="small"
                  text
                  type="danger"
                  @click.stop="removeFrequentSpeaker(speaker.id)"
                >
                  删除
                </el-button>
              </div>
              
              <!-- 添加新的常用发言人 -->
              <div class="add-frequent-speaker" @click="showAddFrequentDialog = true">
                <el-icon size="24" color="#409eff"><Plus /></el-icon>
                <span>添加常用发言人</span>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>

      <!-- 设置说明 -->
      <div class="setting-description">
        <el-icon><InfoFilled /></el-icon>
        <span v-if="settingRange === 'single'">
          只修改当前段落的发言人
        </span>
        <span v-else>
          修改该发言人在整个录音中的所有段落
        </span>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" @click="handleConfirm" :disabled="!speakerName.trim()">
          确定
        </el-button>
      </div>
    </template>
  </el-dialog>

  <!-- 添加常用发言人对话框 -->
  <el-dialog
    v-model="showAddFrequentDialog"
    title="添加常用发言人"
    width="400px"
    class="add-frequent-dialog"
  >
    <el-form :model="newFrequentSpeaker" label-width="80px">
      <el-form-item label="姓名">
        <el-input v-model="newFrequentSpeaker.name" placeholder="请输入发言人姓名" />
      </el-form-item>
      <el-form-item label="颜色">
        <el-color-picker v-model="newFrequentSpeaker.color" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="showAddFrequentDialog = false">取消</el-button>
      <el-button type="primary" @click="addFrequentSpeaker" :disabled="!newFrequentSpeaker.name.trim()">
        添加
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { Plus, InfoFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useSpeakerStore } from '@/stores/speakerStore'

interface Speaker {
  id: number | string
  name: string
  color: string
  number?: string
  segmentCount?: number
  useCount?: number
}

interface SpeakerSettingData {
  speakerName: string
  settingRange: 'single' | 'global'
  targetSpeaker?: Speaker
}

const props = defineProps<{
  modelValue: boolean
  currentSpeakers: Speaker[]
  recordingId: string
  selectedSegment?: {
    id: string
    speakerName: string
    speakerNumber: string
    speakerColor: string
    speakerId: string
  }
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'confirm': [data: SpeakerSettingData]
  'speaker-updated': []
}>()

// 使用speaker store
const speakerStore = useSpeakerStore()

// 对话框显示状态
const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

// 表单数据
const speakerName = ref('')
const settingRange = ref<'single' | 'global'>('single')
const activeTab = ref('current')
const selectedSpeaker = ref<Speaker | null>(null)

// 添加常用发言人
const showAddFrequentDialog = ref(false)
const newFrequentSpeaker = ref({
  name: '',
  color: '#409eff'
})

// 监听选中段落变化，初始化表单
watch(() => props.selectedSegment, (segment) => {
  if (segment) {
    speakerName.value = segment.speakerName
    // 查找对应的发言人
    const currentSpeaker = props.currentSpeakers.find(s => s.number === segment.speakerNumber)
    if (currentSpeaker) {
      selectedSpeaker.value = currentSpeaker
    }
  }
}, { immediate: true })

// 监听对话框打开，重置状态
watch(visible, (show) => {
  if (show) {
    activeTab.value = 'current'
    settingRange.value = 'single'
    if (props.selectedSegment) {
      speakerName.value = props.selectedSegment.speakerName
    }
  }
})

// 选择发言人
const selectSpeaker = (speaker: Speaker) => {
  selectedSpeaker.value = speaker
  speakerName.value = speaker.name
}

// 获取当前发言人头像显示文本
const getCurrentSpeakerAvatarText = (speaker: Speaker) => {
  const name = speaker.name || ''
  
  // 检查是否是默认格式的姓名（如"发言人1"、"发言人2"等）
  const isDefaultName = /^发言人\s*\d+$/.test(name.trim())
  
  // 如果是默认姓名或者姓名为空，显示数字
  if (!name.trim() || isDefaultName) {
    return speaker.number || '1'
  }
  
  // 否则显示姓名的第一个字符
  return name.charAt(0)
}

// 添加常用发言人
const addFrequentSpeaker = async () => {
  if (!newFrequentSpeaker.value.name.trim()) {
    ElMessage.warning('请输入发言人姓名')
    return
  }
  
  try {
    await speakerStore.addFrequentSpeaker({
      name: newFrequentSpeaker.value.name,
      color: newFrequentSpeaker.value.color
    })
    
    // 重置表单
    newFrequentSpeaker.value = {
      name: '',
      color: '#409eff'
    }
    
    showAddFrequentDialog.value = false
  } catch (error) {
    // 错误信息已在store中处理
  }
}

// 删除常用发言人
const removeFrequentSpeaker = async (id: number | string) => {
  try {
    await speakerStore.removeFrequentSpeaker(id)
  } catch (error) {
    // 错误信息已在store中处理
  }
}

// 确认设置
const handleConfirm = async () => {
  if (!speakerName.value.trim()) {
    ElMessage.warning('请输入发言人姓名')
    return
  }
  
  if (!props.selectedSegment) {
    ElMessage.warning('未选择发言段落')
    return
  }
  
  try {
    const frequentSpeakerId = selectedSpeaker.value && typeof selectedSpeaker.value.id === 'number' 
      ? selectedSpeaker.value.id 
      : undefined
    
    await speakerStore.updateSpeakerInRecording(
      props.recordingId,
      props.selectedSegment.speakerId,
      speakerName.value.trim(),
      settingRange.value,
      frequentSpeakerId
    )
    
    // 通知父组件刷新数据
    emit('speaker-updated')
    visible.value = false
  } catch (error) {
    // 错误信息已在store中处理
  }
}

// 取消设置
const handleClose = () => {
  visible.value = false
}

// 初始化加载常用发言人数据
onMounted(() => {
  speakerStore.loadFrequentSpeakers()
})
</script>

<style scoped>
.speaker-setting-dialog {
  .dialog-content {
    padding: 0 4px;
  }

  .setting-section {
    margin-bottom: 20px;
  }

  .speaker-input {
    font-size: 16px;
  }

  .range-selector {
    display: flex;
    gap: 0;
    border-radius: 6px;
    overflow: hidden;
    border: 1px solid #dcdfe6;
    
    .range-button {
      flex: 1;
      border-radius: 0;
      border: none;
      margin: 0;
      
      &:first-child {
        border-right: 1px solid #dcdfe6;
      }
      
      &.el-button--primary {
        background: #409eff;
        color: white;
        border-color: #409eff;
      }
    }
  }

  .speaker-tabs {
    :deep(.el-tabs__header) {
      margin-bottom: 16px;
    }
    
    :deep(.el-tabs__nav-wrap) {
      &::after {
        background: #e4e7ed;
      }
    }
  }

  .speaker-list {
    max-height: 240px;
    overflow-y: auto;
    
    .speaker-item {
      display: flex;
      align-items: center;
      padding: 12px;
      margin-bottom: 8px;
      border: 1px solid #e4e7ed;
      border-radius: 8px;
      cursor: pointer;
      transition: all 0.3s;
      
      &:hover {
        border-color: #409eff;
        background: #f5f7fa;
      }
      
      &.active {
        border-color: #409eff;
        background: #ecf5ff;
      }
      
      .speaker-info {
        flex: 1;
        margin-left: 12px;
        
        .speaker-name {
          font-size: 14px;
          font-weight: 500;
          color: #303133;
          margin-bottom: 4px;
        }
        
        .speaker-stats {
          font-size: 12px;
          color: #909399;
        }
      }
    }
    
    .add-frequent-speaker {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
      border: 1px dashed #c0c4cc;
      border-radius: 8px;
      cursor: pointer;
      color: #409eff;
      transition: all 0.3s;
      
      &:hover {
        border-color: #409eff;
        background: #f5f7fa;
      }
      
      span {
        margin-left: 8px;
        font-size: 14px;
      }
    }
  }

  .setting-description {
    display: flex;
    align-items: center;
    padding: 12px;
    background: #f5f7fa;
    border-radius: 6px;
    font-size: 13px;
    color: #606266;
    
    .el-icon {
      margin-right: 6px;
      color: #909399;
    }
  }

  .dialog-footer {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
  }
}

.add-frequent-dialog {
  :deep(.el-form-item) {
    margin-bottom: 20px;
  }
}
</style> 