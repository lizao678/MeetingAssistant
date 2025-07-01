<script setup lang="ts">
import { ref, computed } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

// 侧边栏折叠状态
const isCollapsed = ref(false)

// 导航菜单配置
const menuItems = [
  {
    index: 'home',
    title: '首页',
    icon: 'House',
    path: '/'
  },
  {
    index: 'recordings',
    title: '我的记录',
    icon: 'Folder',
    path: '/recordings'
  },
  {
    index: 'realtime',
    title: '实时转写',
    icon: 'Microphone',
    path: '/realtime'
  },
  {
    index: 'settings',
    title: '设置',
    icon: 'Setting',
    path: '/settings'
  }
]

// 当前选中的菜单项
const activeMenu = computed(() => {
  return route.name as string || 'realtime'
})

// 切换侧边栏折叠状态
const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}

// 菜单选择处理
const handleMenuSelect = (index: string) => {
  const menuItem = menuItems.find(item => item.index === index)
  if (menuItem) {
    router.push(menuItem.path)
  }
}
</script>

<template>
  <div class="app-container">
    <!-- 侧边栏 -->
    <el-aside :width="isCollapsed ? '64px' : '220px'" class="sidebar">
      <!-- Logo和标题 -->
      <div class="logo-section">
        <div class="logo">
          <el-icon size="32" color="#409eff"><Headphone /></el-icon>
          <span v-show="!isCollapsed" class="app-title">山源听悟</span>
        </div>
        <el-button
          text
          @click="toggleCollapse"
          class="collapse-btn"
          :icon="isCollapsed ? 'Expand' : 'Fold'"
        />
      </div>

      <!-- 导航菜单 -->
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapsed"
        @select="handleMenuSelect"
        class="sidebar-menu"
        router
      >
        <el-menu-item
          v-for="item in menuItems"
          :key="item.index"
          :index="item.index"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <template #title>{{ item.title }}</template>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- 主内容区 -->
    <el-container class="main-container">
      <!-- 顶部导航栏 -->
      <el-header class="header" height="60px">
        <div class="header-content">
          <div class="breadcrumb-section">
            <el-breadcrumb separator="/">
              <el-breadcrumb-item>山源听悟</el-breadcrumb-item>
              <el-breadcrumb-item>
                {{ menuItems.find(item => item.index === activeMenu)?.title || '首页' }}
              </el-breadcrumb-item>
            </el-breadcrumb>
          </div>
          
          <div class="header-actions">
            <el-space>
              <el-tooltip content="文档" placement="bottom">
                <el-button text :icon="'Document'" />
              </el-tooltip>
              <el-tooltip content="关于" placement="bottom">
                <el-button text :icon="'InfoFilled'" />
              </el-tooltip>
            </el-space>
          </div>
    </div>
      </el-header>

      <!-- 页面内容 -->
      <el-main class="main-content">
  <RouterView />
      </el-main>
    </el-container>
  </div>
</template>

<style>
/* 全局样式重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  height: 100%;
  font-family: 'Segoe UI', 'Microsoft YaHei', Arial, sans-serif;
}

#app {
  height: 100%;
}
</style>

<style scoped>
.app-container {
  display: flex;
  height: 100vh;
  background: #f5f7fa;
}

.sidebar {
  background: #fff;
  border-right: 1px solid #e4e7ed;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
  transition: width 0.3s;
  overflow: hidden;
}

.logo-section {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  border-bottom: 1px solid #e4e7ed;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: 600;
  color: #303133;
}

.app-title {
  font-size: 18px;
  white-space: nowrap;
}

.collapse-btn {
  padding: 8px !important;
  color: #909399;
}

.sidebar-menu {
  border: none;
  height: calc(100vh - 60px);
}

.sidebar-menu:not(.el-menu--collapse) {
  width: 220px;
}

.main-container {
  flex: 1;
  overflow: hidden;
}

.header {
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.header-content {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.breadcrumb-section {
  display: flex;
  align-items: center;
}

.header-actions {
    display: flex;
  align-items: center;
  gap: 8px;
}

.main-content {
  padding: 0;
  background: linear-gradient(135deg, #f5f7fa 0%, #f0f2f5 100%);
  overflow-y: auto;
}

/* Element Plus菜单项自定义样式 */
:deep(.el-menu-item) {
  height: 48px;
  line-height: 48px;
  margin: 4px 8px;
  border-radius: 6px;
  transition: all 0.3s;
  }

:deep(.el-menu-item:hover) {
  background-color: #ecf5ff !important;
  color: #409eff;
}

:deep(.el-menu-item.is-active) {
  background-color: #409eff !important;
  color: #fff;
  }

:deep(.el-menu-item.is-active .el-icon) {
  color: #fff;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    height: 100vh;
    z-index: 1000;
  }
  
  .main-container {
    margin-left: 0;
  }
  
  .header-content {
    padding: 0 16px;
  }
}
</style>
