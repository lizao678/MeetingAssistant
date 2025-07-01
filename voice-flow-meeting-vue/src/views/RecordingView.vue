<template>
  <div class="recording-view">
    <el-card shadow="never">
      <template #header>
        <div class="page-header">
          <h2>
            <el-icon><VideoCamera /></el-icon>
            录音管理
          </h2>
          <el-text type="info">录制、管理和回放音频文件</el-text>
        </div>
      </template>
      
      <div class="recording-content">
        <el-empty description="录音功能开发中..." />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
// 这个页面后续会实现录音管理功能
</script>

<style scoped>
.recording-view {
  padding: 20px;
}

.page-header {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.page-header h2 {
  margin: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #303133;
}

.recording-content {
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style> 