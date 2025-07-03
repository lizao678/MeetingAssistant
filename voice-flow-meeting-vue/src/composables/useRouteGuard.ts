import { ref, readonly } from 'vue'
import { onBeforeRouteLeave } from 'vue-router'
import { ElMessageBox } from 'element-plus'

interface RouteGuardOptions {
  // 拦截条件函数
  shouldIntercept: () => boolean
  // 确认对话框配置
  confirmOptions?: {
    title?: string
    message?: string
    confirmButtonText?: string
    cancelButtonText?: string
    type?: 'warning' | 'info' | 'success' | 'error'
  }
  // 确认后的回调函数
  onConfirm?: () => Promise<void> | void
  // 取消后的回调函数
  onCancel?: () => void
}

/**
 * 统一路由拦截管理 Composable
 * 
 * @param options 拦截配置选项
 * @returns 路由拦截相关的响应式状态和方法
 */
export function useRouteGuard(options: RouteGuardOptions) {
  // 智能防重复机制 - 短时间窗口防重复
  let isShowingDialog = false
  let lastCallTime = 0
  let lastUserDecision: boolean | null = null // 记录用户最后的决定
  const DEBOUNCE_TIME = 300 // 300ms防重复窗口期
  
  // 默认配置
  const defaultConfirmOptions = {
    title: '确认退出',
    message: '当前页面有未保存的内容，确认要退出吗？',
    confirmButtonText: '确定退出',
    cancelButtonText: '取消',
    type: 'warning' as const
  }
  
  // 合并配置
  const confirmConfig = {
    ...defaultConfirmOptions,
    ...options.confirmOptions
  }
  
  /**
   * 处理页面离开逻辑
   */
  const handlePageLeave = async (): Promise<boolean> => {
    // 检查是否需要拦截
    if (!options.shouldIntercept()) {
      return true // 不需要拦截，直接允许离开
    }
    
    const currentTime = Date.now()
    
    // 如果正在显示对话框，等待对话框结果
    if (isShowingDialog) {
      console.log('🔄 对话框正在显示中，等待用户操作...')
      // 等待对话框关闭，然后根据结果决定
      while (isShowingDialog) {
        await new Promise(resolve => setTimeout(resolve, 100))
      }
      // 对话框已关闭，返回用户的决定
      console.log('📋 对话框已关闭，用户决定:', lastUserDecision)
      return lastUserDecision ?? false
    }
    
    // 防重复：短时间内的重复调用，返回上次用户的决定
    if (currentTime - lastCallTime < DEBOUNCE_TIME && lastUserDecision !== null) {
      console.log('🔄 检测到短时间内重复调用，返回上次决定:', lastUserDecision)
      return lastUserDecision
    }
    
    lastCallTime = currentTime
    isShowingDialog = true
    
    try {
      // 弹出确认对话框
      await ElMessageBox.confirm(
        confirmConfig.message,
        confirmConfig.title,
        {
          confirmButtonText: confirmConfig.confirmButtonText,
          cancelButtonText: confirmConfig.cancelButtonText,
          type: confirmConfig.type,
          dangerouslyUseHTMLString: false,
          closeOnClickModal: false,
          closeOnPressEscape: false
        }
      )
      
      console.log('✅ 用户确认退出，准备执行回调')
      
      // 用户确认退出，执行确认回调
      if (options.onConfirm) {
        console.log('🔄 执行确认回调中...')
        await options.onConfirm()
        console.log('✅ 确认回调执行完成')
      }
      
      console.log('✅ 准备允许路由跳转')
      lastUserDecision = true // 记录用户确认退出
      return true
    } catch (error) {
      console.log('❌ 用户取消退出')
      // 用户取消退出，执行取消回调
      if (options.onCancel) {
        options.onCancel()
      }
      
      lastUserDecision = false // 记录用户取消退出
      return false
    } finally {
      // 对话框关闭后重置状态
      isShowingDialog = false
      // 一段时间后清除决定记录，避免影响后续操作
      setTimeout(() => {
        lastUserDecision = null
      }, 1000)
    }
  }
  
  // 注册路由离开拦截
  onBeforeRouteLeave(async (to, from, next) => {
    console.log('🚀 路由离开拦截触发，从', from.path, '到', to.path)
    
    const canLeave = await handlePageLeave()
    console.log('🔄 handlePageLeave 返回结果:', canLeave)
    
    if (canLeave) {
      console.log('✅ 允许路由跳转，调用 next()')
      next() // 允许跳转
    } else {
      console.log('❌ 阻止路由跳转，调用 next(false)')
      next(false) // 阻止跳转
    }
  })
  
  return {
    // 方法
    handlePageLeave,
    triggerLeaveConfirm: handlePageLeave // 手动触发离开确认
  }
}

/**
 * 预设的录音页面路由拦截配置
 */
export function useRecordingRouteGuard(isRecording: () => boolean, onStopRecording?: () => Promise<void>) {
  return useRouteGuard({
    shouldIntercept: isRecording,
    confirmOptions: {
      title: '确认退出',
      message: '当前录音未保存，确认要退出吗？',
      confirmButtonText: '确定退出',
      cancelButtonText: '取消',
      type: 'warning'
    },
    onConfirm: onStopRecording
  })
}

/**
 * 预设的表单页面路由拦截配置
 */
export function useFormRouteGuard(hasUnsavedChanges: () => boolean, onSave?: () => Promise<void>) {
  return useRouteGuard({
    shouldIntercept: hasUnsavedChanges,
    confirmOptions: {
      title: '确认退出',
      message: '表单有未保存的修改，确认要退出吗？',
      confirmButtonText: '确定退出',
      cancelButtonText: '取消',
      type: 'warning'
    },
    onConfirm: onSave
  })
} 