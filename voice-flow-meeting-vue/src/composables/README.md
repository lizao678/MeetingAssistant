# 路由拦截管理 Composables

## 概述

`useRouteGuard` 提供了统一的路由拦截管理机制，避免重复代码并提供更好的用户体验。

## 基础用法

### 1. 通用路由拦截

```typescript
import { useRouteGuard } from '@/composables/useRouteGuard'

export default {
  setup() {
    const hasUnsavedChanges = ref(false)
    
    // 基础路由拦截
    const { triggerLeaveConfirm } = useRouteGuard({
      shouldIntercept: () => hasUnsavedChanges.value,
      confirmOptions: {
        title: '确认退出',
        message: '有未保存的修改，确认要退出吗？',
        confirmButtonText: '确定退出',
        cancelButtonText: '取消',
        type: 'warning'
      },
      onConfirm: async () => {
        // 用户确认退出时的处理逻辑
        await saveData()
      },
      onCancel: () => {
        // 用户取消退出时的处理逻辑
        console.log('用户取消了退出操作')
      }
    })
    
    return {
      triggerLeaveConfirm
    }
  }
}
```

### 2. 录音页面专用拦截

```typescript
import { useRecordingRouteGuard } from '@/composables/useRouteGuard'

export default {
  setup() {
    const isRecording = ref(false)
    
    // 录音页面专用拦截
    useRecordingRouteGuard(
      () => isRecording.value, // 拦截条件
      async () => {
        // 确认退出时停止录音
        await stopRecording(false)
      }
    )
  }
}
```

### 3. 表单页面专用拦截

```typescript
import { useFormRouteGuard } from '@/composables/useRouteGuard'

export default {
  setup() {
    const formDirty = ref(false)
    
    // 表单页面专用拦截
    useFormRouteGuard(
      () => formDirty.value, // 拦截条件
      async () => {
        // 确认退出时自动保存
        await autoSave()
      }
    )
  }
}
```

## API 参考

### useRouteGuard(options)

#### 参数

- `options.shouldIntercept: () => boolean` - 是否需要拦截的条件函数
- `options.confirmOptions?` - 确认对话框配置
  - `title?: string` - 对话框标题
  - `message?: string` - 对话框消息
  - `confirmButtonText?: string` - 确认按钮文本
  - `cancelButtonText?: string` - 取消按钮文本
  - `type?: 'warning' | 'info' | 'success' | 'error'` - 对话框类型
- `options.onConfirm?: () => Promise<void> | void` - 确认退出时的回调
- `options.onCancel?: () => void` - 取消退出时的回调

#### 返回值

- `handlePageLeave: () => Promise<boolean>` - 手动触发页面离开处理
- `triggerLeaveConfirm: () => Promise<boolean>` - 手动触发离开确认

### useRecordingRouteGuard(isRecording, onStopRecording?)

录音页面的预设拦截配置。

#### 参数

- `isRecording: () => boolean` - 是否正在录音
- `onStopRecording?: () => Promise<void>` - 停止录音的回调函数

### useFormRouteGuard(hasUnsavedChanges, onSave?)

表单页面的预设拦截配置。

#### 参数

- `hasUnsavedChanges: () => boolean` - 是否有未保存的修改
- `onSave?: () => Promise<void>` - 保存数据的回调函数

## 特性

### 1. 类型安全

完整的 TypeScript 类型定义，提供良好的开发体验。

### 2. 灵活配置

支持自定义确认对话框的各种配置选项。

### 3. 预设配置

提供录音和表单场景的预设配置，开箱即用。

### 4. 简洁易用

简化的API设计，避免复杂的状态管理。

## 最佳实践

### 1. 合理设置拦截条件

```typescript
// ✅ 好的实践
shouldIntercept: () => isRecording.value && !isPaused.value

// ❌ 避免复杂的副作用
shouldIntercept: () => {
  // 避免在此函数中执行副作用操作
  console.log('checking...') // ❌
  return hasChanges.value
}
```

### 2. 处理异步操作

```typescript
onConfirm: async () => {
  try {
    await saveData()
    await cleanup()
  } catch (error) {
    // 处理错误
    console.error('保存失败:', error)
  }
}
```

## 使用场景

- ✅ 录音/视频录制页面
- ✅ 表单编辑页面
- ✅ 数据输入页面
- ✅ 任何需要防止意外离开的页面

## 注意事项

1. **性能考虑**：`shouldIntercept` 函数会在每次路由变化时调用，避免在其中执行昂贵的操作
2. **异步处理**：`onConfirm` 回调支持异步操作，确保在退出前完成必要的清理工作 