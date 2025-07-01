<template>
  <div class="analysis-view">
    <el-card shadow="never">
      <template #header>
        <div class="page-header">
          <h2>
            <el-icon><TrendCharts /></el-icon>
            详细分析
          </h2>
          <el-text type="info">深度分析会议内容和发言人数据</el-text>
        </div>
      </template>
      
      <div class="analysis-content">
        <el-empty description="详细分析功能开发中..." />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
// 这个页面后续会实现详细分析功能
</script>

<style scoped>
.analysis-view {
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

.analysis-content {
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style> 