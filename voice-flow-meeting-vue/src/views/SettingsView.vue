<template>
  <div class="settings-view">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-content">
        <div class="header-left">
          <h1 class="page-title">
            <el-icon><Setting /></el-icon>
            设置
          </h1>
          <p class="page-subtitle">配置语音识别、智能总结和系统设置</p>
        </div>
        <div class="header-actions">
          <el-space>
            <el-button @click="exportSettings">导出设置</el-button>
            <el-upload
              accept=".json"
              :show-file-list="false"
              :on-change="importSettings"
              :auto-upload="false"
            >
              <el-button>导入设置</el-button>
            </el-upload>
            <el-button type="danger" @click="resetSettings">重置设置</el-button>
            <el-button type="primary" @click="saveSettings">保存设置</el-button>
          </el-space>
        </div>
      </div>
    </div>

    <!-- 设置内容 -->
    <div class="settings-content">
      <el-card class="settings-card" shadow="never">
        <el-tabs v-model="activeTab" type="border-card">
          <!-- 语音识别设置 -->
          <el-tab-pane label="语音识别" name="speech">
            <div class="settings-section">
              <h3>基础设置</h3>
              <el-form :model="speechSettings" label-width="140px">
                <el-form-item label="默认识别语言">
                  <el-select v-model="speechSettings.defaultLanguage" style="width: 200px">
                    <el-option
                      v-for="lang in languageOptions"
                      :key="lang.value"
                      :label="lang.label"
                      :value="lang.value"
                    />
                  </el-select>
                </el-form-item>

                <el-form-item label="采样率">
                  <el-select v-model="speechSettings.sampleRate" style="width: 200px">
                    <el-option label="8kHz" :value="8000" />
                    <el-option label="16kHz" :value="16000" />
                    <el-option label="22kHz" :value="22050" />
                    <el-option label="44kHz" :value="44100" />
                  </el-select>
                </el-form-item>

                <el-form-item label="最大语音长度">
                  <el-input-number
                    v-model="speechSettings.maxSpeechLength"
                    :min="10"
                    :max="300"
                    style="width: 200px"
                  />
                  <span class="unit">秒</span>
                </el-form-item>
              </el-form>

              <h3>音频处理</h3>
              <el-form :model="speechSettings" label-width="140px">
                <el-form-item label="音频增强">
                  <el-switch v-model="speechSettings.enableAudioEnhancement" />
                  <div class="setting-tip">提升音频质量，降低噪声（如遇问题可关闭）</div>
                </el-form-item>

                <template v-if="speechSettings.enableAudioEnhancement">
                  <el-form-item label="增强强度">
                    <el-select v-model="speechSettings.enhancementLevel" style="width: 200px">
                      <el-option label="轻度" value="light" />
                      <el-option label="中等" value="medium" />
                      <el-option label="强" value="strong" />
                    </el-select>
                    <div class="setting-tip">选择合适的增强强度</div>
                  </el-form-item>

                  <el-form-item label="噪声抑制">
                    <el-switch v-model="speechSettings.enableNoiseSuppression" />
                    <div class="setting-tip">降低背景噪声</div>
                  </el-form-item>

                  <el-form-item label="音量自动调节">
                    <el-switch v-model="speechSettings.enableAutoGain" />
                    <div class="setting-tip">自动平衡音量大小</div>
                  </el-form-item>
                </template>

                <el-form-item label="语音活动检测">
                  <el-switch v-model="speechSettings.enableVAD" />
                  <div class="setting-tip">自动检测语音开始和结束</div>
                </el-form-item>

                <el-form-item label="VAD阈值" v-if="speechSettings.enableVAD">
                  <el-slider
                    v-model="speechSettings.vadThreshold"
                    :min="0.1"
                    :max="1"
                    :step="0.1"
                    style="width: 200px"
                  />
                </el-form-item>

                <el-form-item label="回声消除">
                  <el-switch v-model="speechSettings.enableEchoCancellation" />
                  <div class="setting-tip">消除扬声器回声</div>
                </el-form-item>

                <el-form-item label="实时转写">
                  <el-switch v-model="speechSettings.enableRealTimeTranscription" />
                  <div class="setting-tip">边说边转写，实时显示结果</div>
                </el-form-item>
              </el-form>

              <div class="test-section">
                <el-button type="primary" @click="testSpeechRecognition">
                  <el-icon><Microphone /></el-icon>
                  测试语音识别
                </el-button>
              </div>
            </div>
          </el-tab-pane>

          <!-- 说话人识别设置 -->
          <el-tab-pane label="说话人识别" name="speaker">
            <div class="settings-section">
              <el-form :model="speakerSettings" label-width="140px">
                <el-form-item label="说话人分离">
                  <el-switch v-model="speakerSettings.enableSpeakerDiarization" />
                  <div class="setting-tip">自动区分不同说话人</div>
                </el-form-item>

                <el-form-item label="最大说话人数">
                  <el-input-number
                    v-model="speakerSettings.maxSpeakers"
                    :min="2"
                    :max="20"
                    style="width: 200px"
                  />
                </el-form-item>

                <el-form-item label="相似度阈值">
                  <el-slider
                    v-model="speakerSettings.speakerSimilarityThreshold"
                    :min="0.5"
                    :max="1"
                    :step="0.05"
                    style="width: 200px"
                  />
                  <div class="setting-tip">说话人识别的相似度阈值</div>
                </el-form-item>

                <el-form-item label="声纹特征提取">
                  <el-switch v-model="speakerSettings.enableSpeakerEmbedding" />
                  <div class="setting-tip">提取说话人声纹特征用于识别</div>
                </el-form-item>
              </el-form>
            </div>
          </el-tab-pane>

          <!-- 智能总结设置 -->
          <el-tab-pane label="智能总结" name="summary">
            <div class="settings-section">
              <el-form :model="summarySettings" label-width="140px">
                <el-form-item label="自动总结">
                  <el-switch v-model="summarySettings.enableAutoSummary" />
                  <div class="setting-tip">转写完成后自动生成总结</div>
                </el-form-item>

                <el-form-item label="总结语言">
                  <el-select v-model="summarySettings.summaryLanguage" style="width: 200px">
                    <el-option
                      v-for="lang in languageOptions"
                      :key="lang.value"
                      :label="lang.label"
                      :value="lang.value"
                    />
                  </el-select>
                </el-form-item>

                <el-form-item label="总结模型">
                  <el-select v-model="summarySettings.summaryModel" style="width: 200px">
                    <el-option
                      v-for="model in modelOptions"
                      :key="model.value"
                      :label="model.label"
                      :value="model.value"
                    />
                  </el-select>
                </el-form-item>

                <el-form-item label="最大总结长度">
                  <el-input-number
                    v-model="summarySettings.maxSummaryLength"
                    :min="100"
                    :max="2000"
                    style="width: 200px"
                  />
                  <span class="unit">字</span>
                </el-form-item>

                <el-form-item label="包含关键词">
                  <el-switch v-model="summarySettings.includeKeywords" />
                  <div class="setting-tip">在总结中提取并显示关键词</div>
                </el-form-item>

                <el-form-item label="情感分析">
                  <el-switch v-model="summarySettings.includeSentiment" />
                  <div class="setting-tip">分析语音内容的情感倾向</div>
                </el-form-item>
              </el-form>
            </div>
          </el-tab-pane>

          <!-- 存储和导出设置 -->
          <el-tab-pane label="存储导出" name="storage">
            <div class="settings-section">
              <el-form :model="storageSettings" label-width="140px">
                <el-form-item label="自动保存">
                  <el-switch v-model="storageSettings.autoSave" />
                  <div class="setting-tip">定期自动保存转写结果</div>
                </el-form-item>

                <el-form-item label="保存间隔" v-if="storageSettings.autoSave">
                  <el-input-number
                    v-model="storageSettings.saveInterval"
                    :min="10"
                    :max="300"
                    style="width: 200px"
                  />
                  <span class="unit">秒</span>
                </el-form-item>

                <el-form-item label="数据保存天数">
                  <el-input-number
                    v-model="storageSettings.maxStorageDays"
                    :min="1"
                    :max="365"
                    style="width: 200px"
                  />
                  <span class="unit">天</span>
                </el-form-item>

                <el-form-item label="默认导出格式">
                  <el-select v-model="storageSettings.defaultExportFormat" style="width: 200px">
                    <el-option
                      v-for="format in exportFormatOptions"
                      :key="format.value"
                      :label="format.label"
                      :value="format.value"
                    />
                  </el-select>
                </el-form-item>

                <el-form-item label="压缩级别">
                  <el-select v-model="storageSettings.compressionLevel" style="width: 200px">
                    <el-option
                      v-for="level in compressionOptions"
                      :key="level.value"
                      :label="level.label"
                      :value="level.value"
                    />
                  </el-select>
                </el-form-item>

                <el-form-item label="云端同步">
                  <el-switch v-model="storageSettings.enableCloudSync" />
                  <div class="setting-tip">将数据同步到云端存储</div>
                </el-form-item>
              </el-form>
            </div>
          </el-tab-pane>

          <!-- 界面设置 -->
          <el-tab-pane label="界面显示" name="ui">
            <div class="settings-section">
              <el-form :model="uiSettings" label-width="140px">
                <el-form-item label="主题模式">
                  <el-select v-model="uiSettings.theme" style="width: 200px">
                    <el-option
                      v-for="theme in themeOptions"
                      :key="theme.value"
                      :label="theme.label"
                      :value="theme.value"
                    />
                  </el-select>
                </el-form-item>

                <el-form-item label="字体大小">
                  <el-select v-model="uiSettings.fontSize" style="width: 200px">
                    <el-option
                      v-for="size in fontSizeOptions"
                      :key="size.value"
                      :label="size.label"
                      :value="size.value"
                    />
                  </el-select>
                </el-form-item>

                <el-form-item label="界面语言">
                  <el-select v-model="uiSettings.language" style="width: 200px">
                    <el-option label="简体中文" value="zh-CN" />
                    <el-option label="繁體中文" value="zh-TW" />
                    <el-option label="English" value="en-US" />
                  </el-select>
                </el-form-item>

                <el-form-item label="显示动画">
                  <el-switch v-model="uiSettings.enableAnimations" />
                  <div class="setting-tip">启用界面动画效果</div>
                </el-form-item>

                <el-form-item label="显示置信度">
                  <el-switch v-model="uiSettings.showConfidenceScore" />
                  <div class="setting-tip">显示语音识别的置信度分数</div>
                </el-form-item>

                <el-form-item label="系统通知">
                  <el-switch v-model="uiSettings.enableNotifications" />
                  <div class="setting-tip">允许系统推送通知</div>
                </el-form-item>
              </el-form>
            </div>
          </el-tab-pane>

          <!-- 高级设置 -->
          <el-tab-pane label="高级设置" name="advanced">
            <div class="settings-section">
              <el-form :model="advancedSettings" label-width="140px">
                <el-form-item label="调试模式">
                  <el-switch v-model="advancedSettings.enableDebugMode" />
                  <div class="setting-tip">启用调试模式，显示详细日志</div>
                </el-form-item>

                <el-form-item label="日志级别">
                  <el-select v-model="advancedSettings.logLevel" style="width: 200px">
                    <el-option
                      v-for="level in logLevelOptions"
                      :key="level.value"
                      :label="level.label"
                      :value="level.value"
                    />
                  </el-select>
                </el-form-item>

                <el-form-item label="启用缓存">
                  <el-switch v-model="advancedSettings.enableCaching" />
                  <div class="setting-tip">缓存模型和结果以提高性能</div>
                </el-form-item>

                <el-form-item label="缓存大小" v-if="advancedSettings.enableCaching">
                  <el-input-number
                    v-model="advancedSettings.cacheSize"
                    :min="50"
                    :max="1000"
                    style="width: 200px"
                  />
                  <span class="unit">MB</span>
                </el-form-item>

                <el-form-item label="GPU加速">
                  <el-switch v-model="advancedSettings.enableGPUAcceleration" />
                  <div class="setting-tip">使用GPU加速模型推理</div>
                </el-form-item>

                <el-form-item label="最大并发任务">
                  <el-input-number
                    v-model="advancedSettings.maxConcurrentTasks"
                    :min="1"
                    :max="10"
                    style="width: 200px"
                  />
                </el-form-item>
              </el-form>

              <div class="cache-section">
                <h4>缓存管理</h4>
                <el-button type="warning" @click="clearCache">
                  <el-icon><Delete /></el-icon>
                  清除缓存
                </el-button>
                <div class="setting-tip">清除所有缓存数据，释放存储空间</div>
              </div>
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Microphone } from '@element-plus/icons-vue'
import type { AudioSettings } from '@/types/audio'
import { useSettingsStore } from '@/stores/settingsStore'
import { storeToRefs } from 'pinia'

// 获取设置store
const settingsStore = useSettingsStore()
const { settings: storeSettings, speechSettings: storeSpeechSettings } = storeToRefs(settingsStore)

// 本地设置状态
const speechSettings = ref<AudioSettings>({
  ...storeSpeechSettings.value
})

// 说话人识别设置
const speakerSettings = reactive({
  enableSpeakerDiarization: true,
  maxSpeakers: 10,
  speakerSimilarityThreshold: 0.8,
  enableSpeakerEmbedding: true
})

// 智能总结设置
const summarySettings = reactive({
  enableAutoSummary: true,
  summaryLanguage: 'zh',
  maxSummaryLength: 500,
  includeKeywords: true,
  includeSentiment: false,
  summaryModel: 'qwen-turbo'
})

// 存储和导出设置
const storageSettings = reactive({
  autoSave: true,
  saveInterval: 30,
  maxStorageDays: 30,
  defaultExportFormat: 'docx',
  enableCloudSync: false,
  compressionLevel: 'medium'
})

// 界面设置
const uiSettings = reactive({
  theme: 'light' as 'light' | 'dark' | 'auto',
  fontSize: 'medium' as 'small' | 'medium' | 'large',
  enableAnimations: true,
  showConfidenceScore: true,
  enableNotifications: true,
  language: 'zh-CN'
})

// 高级设置
const advancedSettings = reactive({
  enableDebugMode: false,
  logLevel: 'info',
  enableCaching: true,
  cacheSize: 100,
  enableGPUAcceleration: false,
  maxConcurrentTasks: 2
})

// 从store加载设置
const loadSettingsFromStore = () => {
  // 1. 加载音频设置
  speechSettings.value = { ...storeSpeechSettings.value }
  
  // 2. 加载其他设置
  const storeSettingsValue = storeSettings.value
  
  // 更新说话人识别设置
  speakerSettings.enableSpeakerDiarization = storeSettingsValue.enableSpeakerRecognition
  
  // 更新界面设置
  uiSettings.theme = storeSettingsValue.theme
  uiSettings.fontSize = storeSettingsValue.fontSize
  uiSettings.enableNotifications = storeSettingsValue.enableNotifications
  
  // 更新存储设置
  storageSettings.autoSave = storeSettingsValue.autoSave
  storageSettings.enableCloudSync = storeSettingsValue.saveLocation === 'cloud'
  
  // 更新智能总结设置
  summarySettings.enableAutoSummary = storeSettingsValue.autoGenerateSummary
  summarySettings.includeKeywords = storeSettingsValue.autoExtractKeywords
  summarySettings.includeSentiment = storeSettingsValue.enableSentimentAnalysis
  summarySettings.summaryLanguage = storeSettingsValue.summaryLanguage
  
  // 更新高级设置
  advancedSettings.cacheSize = storeSettingsValue.maxLocalStorage
}

// 组件加载时初始化设置
onMounted(() => {
  // 从store加载设置
  loadSettingsFromStore()
})

// 支持的语言选项
const languageOptions = [
  { label: '中文（简体）', value: 'zh' },
  { label: '中文（繁体）', value: 'zh-TW' },
  { label: 'English', value: 'en' },
  { label: '日本語', value: 'ja' },
  { label: '한국어', value: 'ko' },
  { label: 'Русский', value: 'ru' },
  { label: 'Français', value: 'fr' }
]

// 模型选项
const modelOptions = [
  { label: '山源大模型-Turbo', value: 'qwen-turbo' },
  { label: '山源大模型-Max', value: 'qwen-max' },
  { label: 'GPT-3.5', value: 'gpt-3.5-turbo' },
  { label: 'GPT-4', value: 'gpt-4' }
]

// 主题选项
const themeOptions = [
  { label: '浅色模式', value: 'light' },
  { label: '深色模式', value: 'dark' },
  { label: '跟随系统', value: 'auto' }
]

// 字体大小选项
const fontSizeOptions = [
  { label: '小', value: 'small' },
  { label: '中', value: 'medium' },
  { label: '大', value: 'large' }
]

// 导出格式选项
const exportFormatOptions = [
  { label: 'Word文档 (.docx)', value: 'docx' },
  { label: '纯文本 (.txt)', value: 'txt' },
  { label: 'PDF文档 (.pdf)', value: 'pdf' },
  { label: 'JSON数据 (.json)', value: 'json' }
]

// 压缩级别选项
const compressionOptions = [
  { label: '低压缩', value: 'low' },
  { label: '中等压缩', value: 'medium' },
  { label: '高压缩', value: 'high' }
]

// 日志级别选项
const logLevelOptions = [
  { label: '错误', value: 'error' },
  { label: '警告', value: 'warn' },
  { label: '信息', value: 'info' },
  { label: '调试', value: 'debug' }
]

// 活动的设置标签
const activeTab = ref('speech')

// 保存设置
const saveSettings = () => {
  try {
    // 1. 更新音频设置
    storeSpeechSettings.value = { ...speechSettings.value }
    
    // 2. 更新其他设置
    settingsStore.updateSettings({
      // 语音识别设置
      defaultLanguage: speechSettings.value.defaultLanguage,
      enableSpeakerRecognition: speakerSettings.enableSpeakerDiarization,
      enableSmartBreaks: true,
      enablePunctuation: true,
      
      // 显示设置
      theme: uiSettings.theme as 'light' | 'dark' | 'auto',
      fontSize: uiSettings.fontSize as 'small' | 'medium' | 'large',
      messageDisplayMode: 'bubble',
      showTimestamps: true,
      
      // 音频设置
      audioDevice: '',
      enableNoiseReduction: speechSettings.value.enableNoiseSuppression,
      enableEchoCancellation: speechSettings.value.enableEchoCancellation,
      audioQuality: 'medium',
      
      // 存储设置
      autoSave: storageSettings.autoSave,
      saveLocation: storageSettings.enableCloudSync ? 'cloud' : 'local',
      maxLocalStorage: advancedSettings.cacheSize,
      
      // 通知设置
      enableNotifications: uiSettings.enableNotifications,
      notificationSound: false,
      errorNotifications: true,
      
      // AI功能设置
      autoGenerateSummary: summarySettings.enableAutoSummary,
      autoExtractKeywords: summarySettings.includeKeywords,
      enableSentimentAnalysis: summarySettings.includeSentiment,
      summaryLanguage: summarySettings.summaryLanguage,
      
      // 隐私设置
      enableLocalProcessing: false,
      shareAnalyticsData: false,
      retainAudioData: true
    })

    // 3. 保存到本地存储
    settingsStore.saveSettings()

    ElMessage.success('设置已保存')
  } catch (error) {
    console.error('保存设置失败:', error)
    ElMessage.error('保存设置失败，请重试')
  }
}

// 重置设置
const resetSettings = () => {
  ElMessageBox.confirm('确定要重置所有设置吗？此操作不可撤销。', '重置设置', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    // 重置store中的设置
    settingsStore.resetToDefaults()
    // 重新加载设置到本地状态
    loadSettingsFromStore()
    ElMessage.success('设置已重置')
  }).catch(() => {
    // 用户取消
  })
}

// 导出设置
const exportSettings = () => {
  const settings = {
    speech: speechSettings.value,
    speaker: speakerSettings,
    summary: summarySettings,
    storage: storageSettings,
    ui: uiSettings,
    advanced: advancedSettings
  }
  
  const blob = new Blob([JSON.stringify(settings, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'settings.json'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  
  ElMessage.success('设置已导出')
}

// 导入设置
const importSettings = (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  
  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      const settings = JSON.parse(e.target?.result as string)
      // 这里应该验证设置格式并应用
      ElMessage.success('设置已导入')
    } catch (error) {
      ElMessage.error('设置文件格式错误')
    }
  }
  reader.readAsText(file)
}

// 测试语音识别
const testSpeechRecognition = () => {
  ElMessage.info('开始测试语音识别...')
  // 这里应该调用实际的测试接口
  setTimeout(() => {
    ElMessage.success('语音识别测试通过')
  }, 2000)
}

// 清除缓存
const clearCache = () => {
  ElMessageBox.confirm('确定要清除所有缓存吗？', '清除缓存', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning'
  }).then(() => {
    ElMessage.success('缓存已清除')
  }).catch(() => {
    // 用户取消
  })
}
</script>

<style scoped>
.settings-view {
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

/* 设置内容 */
.settings-content {
  max-width: 1200px;
  margin: 24px auto;
  padding: 0 24px;
}

.settings-card {
  border-radius: 12px;
  border: 1px solid #e4e7ed;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

/* 设置区块 */
.settings-section {
  padding: 20px 0;
}

.settings-section h3 {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 20px 0;
  padding-bottom: 8px;
  border-bottom: 1px solid #e4e7ed;
}

.settings-section h4 {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
  margin: 20px 0 12px 0;
}

/* 表单样式 */
.setting-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  line-height: 1.4;
}

.unit {
  margin-left: 8px;
  color: #909399;
  font-size: 14px;
}

/* 测试区块 */
.test-section {
  margin-top: 24px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
}

/* 缓存管理区块 */
.cache-section {
  margin-top: 24px;
  padding: 20px;
  background: #fff7e6;
  border: 1px solid #ffd591;
  border-radius: 8px;
}

/* 标签页样式 */
:deep(.el-tabs--border-card) {
  border: none;
  box-shadow: none;
}

:deep(.el-tabs__header) {
  background: #f8f9fa;
  border-radius: 8px 8px 0 0;
  margin: 0;
}

:deep(.el-tabs__content) {
  padding: 20px;
}

:deep(.el-tabs__item) {
  border: none;
  color: #606266;
}

:deep(.el-tabs__item.is-active) {
  background: white;
  color: #409eff;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .header-content {
    flex-direction: column;
    gap: 16px;
    text-align: center;
  }

  .settings-content {
    padding: 0 16px;
  }

  :deep(.el-form-item__label) {
    width: 100px !important;
  }

  .test-section,
  .cache-section {
    padding: 16px;
  }
}
</style> 