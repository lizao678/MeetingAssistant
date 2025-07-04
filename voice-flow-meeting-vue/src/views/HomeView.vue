<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()

// 最近记录数据（模拟）
const recentRecords = ref([
  {
    id: '1',
    title: '2025-01-30 16:11 记录',
    duration: '00:37',
    totalDuration: '今天 16:11',
    tags: ['互联网资讯', '市场动态', '情感'],
    status: 'completed'
  },
  {
    id: '2', 
    title: '2025-01-30 10:38 记录',
    duration: '00:36',
    totalDuration: '今天 10:38',
    tags: ['谢谢'],
    status: 'completed'
  },
  {
    id: '3',
    title: '2025-01-30 09:55 记录', 
    duration: '11:22',
    totalDuration: '今天 09:55',
    tags: ['逻辑', '沟通', '角色', '效果', '内容'],
    status: 'completed'
  },
  {
    id: '4',
    title: '2025-01-30 09:54 记录',
    duration: '00:55', 
    totalDuration: '今天 09:54',
    tags: [],
    status: 'completed'
  }
])

// 功能卡片配置
const featureCards = [
  {
    title: '开启实时记录',
    subtitle: '实时语音转文字',
    description: '同步翻译，智能总结要点',
    icon: 'Microphone',
    color: '#667AFA',
    bgGradient: 'linear-gradient(135deg, #667AFA 0%, #9BB5FF 100%)',
    route: '/realtime'
  },
  {
    title: '上传音视频',
    subtitle: '音视频转文字',
    description: '区分发言人，一键导出',
    icon: 'VideoPlay',
    color: '#4ECDC4',
    bgGradient: 'linear-gradient(135deg, #4ECDC4 0%, #44A08D 100%)',
    route: '/upload'
  },
//   {
//     title: '智能总结',
//     subtitle: '输入RSS订阅链接',
//     description: '无需下载，智能提炼关键',
//     icon: 'Document',
//     color: '#45B7D1',
//     bgGradient: 'linear-gradient(135deg, #45B7D1 0%, #96C93D 100%)',
//     route: '/upload'
//   }
]

// 导航到功能页面
const navigateToFeature = (route: string) => {
  router.push(route)
}

// 播放录音
const playRecord = (record: any) => {
  ElMessage.success(`播放录音: ${record.title}`)
}

// 查看录音详情
const viewRecord = (record: any) => {
  router.push(`/recording/${record.id}`)
}
</script>

<template>
  <div class="home-view">
    <!-- 顶部标题区域 -->
    <div class="hero-section">
      <div class="hero-content">
        <h1 class="hero-title">听悟一下，随心"录"播客</h1>
        <p class="hero-subtitle">实时语音识别 · 智能会议总结 · 多语言支持</p>
      </div>
      <div class="hero-decoration">
        <div class="wave-pattern"></div>
      </div>
    </div>

    <!-- 功能卡片区域 -->
    <div class="features-section">
      <div class="feature-cards">
        <div
          v-for="card in featureCards"
          :key="card.title"
          class="feature-card"
          :style="{ background: card.bgGradient }"
          @click="navigateToFeature(card.route)"
        >
          <div class="card-content">
            <div class="card-icon">
              <el-icon :size="32" :color="'white'">
                <component :is="card.icon" />
              </el-icon>
            </div>
            <div class="card-info">
              <h3 class="card-title">{{ card.title }}</h3>
              <p class="card-subtitle">{{ card.subtitle }}</p>
              <p class="card-description">{{ card.description }}</p>
            </div>
          </div>
          <div class="card-action">
            <el-icon size="16" color="white">
              <ArrowRight />
            </el-icon>
          </div>
        </div>
      </div>
    </div>

    <!-- 最近记录区域 -->
    <div class="recent-section">
      <div class="section-header">
        <h2>最近</h2>
        <el-button text type="primary" @click="router.push('/recordings')">
          查看全部
          <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>

      <div class="records-grid">
        <div
          v-for="record in recentRecords"
          :key="record.id"
          class="record-card"
          @click="viewRecord(record)"
        >
          <div class="record-header">
            <h3 class="record-title">{{ record.title }}</h3>
            <el-button
              text
              size="small"
              :icon="'VideoPlay'"
              @click.stop="playRecord(record)"
            />
          </div>
          
          <div class="record-meta">
            <span class="duration">{{ record.duration }}</span>
            <span class="total-duration">{{ record.totalDuration }}</span>
          </div>

          <div v-if="record.tags.length > 0" class="record-tags">
            <el-tag
              v-for="tag in record.tags"
              :key="tag"
              size="small"
              type="info"
              effect="plain"
            >
              {{ tag }}
            </el-tag>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home-view {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #f0f2f5 100%);
  position: relative;
  overflow-x: hidden;
}

/* 英雄区域 */
.hero-section {
  position: relative;
  padding: 60px 40px 40px;
  text-align: center;
  background: linear-gradient(135deg, #667AFA 0%, #9BB5FF 100%);
  color: white;
  overflow: hidden;
}

.hero-content {
  position: relative;
  z-index: 2;
  max-width: 800px;
  margin: 0 auto;
}

.hero-title {
  font-size: 42px;
  font-weight: 700;
  margin-bottom: 16px;
  line-height: 1.2;
}

.hero-subtitle {
  font-size: 18px;
  opacity: 0.9;
  margin-bottom: 0;
}

.hero-decoration {
  position: absolute;
  right: -200px;
  top: 50%;
  transform: translateY(-50%);
  width: 600px;
  height: 400px;
  opacity: 0.1;
}

.wave-pattern {
  width: 100%;
  height: 100%;
  background: repeating-linear-gradient(
    45deg,
    transparent,
    transparent 10px,
    rgba(255, 255, 255, 0.1) 10px,
    rgba(255, 255, 255, 0.1) 20px
  );
  border-radius: 50%;
}

/* 功能卡片区域 */
.features-section {
  padding: 40px;
  max-width: 1200px;
  margin: 0 auto;
}

.feature-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 24px;
  margin-bottom: 60px;
}

.feature-card {
  border-radius: 16px;
  padding: 32px;
  color: white;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 140px;
}

.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 48px rgba(0, 0, 0, 0.2);
}

.feature-card::before {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 120px;
  height: 120px;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
  border-radius: 50%;
  transform: translate(40px, -40px);
}

.card-content {
  display: flex;
  align-items: center;
  gap: 20px;
  flex: 1;
}

.card-icon {
  width: 64px;
  height: 64px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(10px);
}

.card-info {
  flex: 1;
}

.card-title {
  font-size: 20px;
  font-weight: 600;
  margin-bottom: 4px;
}

.card-subtitle {
  font-size: 14px;
  opacity: 0.9;
  margin-bottom: 8px;
}

.card-description {
  font-size: 13px;
  opacity: 0.8;
  line-height: 1.4;
}

.card-action {
  width: 32px;
  height: 32px;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(10px);
}

/* 最近记录区域 */
.recent-section {
  padding: 0 40px 40px;
  max-width: 1200px;
  margin: 0 auto;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.section-header h2 {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}

.records-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
}

.record-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid #f0f2f5;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.record-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  border-color: #e4e7ed;
}

.record-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.record-title {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
  margin: 0;
  line-height: 1.4;
  flex: 1;
}

.record-meta {
  display: flex;
  gap: 16px;
  margin-bottom: 12px;
  font-size: 14px;
  color: #909399;
}

.duration {
  font-weight: 500;
}

.record-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .hero-section {
    padding: 40px 20px 30px;
  }
  
  .hero-title {
    font-size: 32px;
  }
  
  .hero-subtitle {
    font-size: 16px;
  }

  .features-section {
    padding: 30px 20px;
  }

  .feature-cards {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .feature-card {
    padding: 24px;
    min-height: 120px;
  }

  .card-content {
    gap: 16px;
  }

  .card-icon {
    width: 56px;
    height: 56px;
  }

  .recent-section {
    padding: 0 20px 30px;
  }

  .records-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
}
</style>
