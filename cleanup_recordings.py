#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import sys

def get_recordings():
    """获取所有录音记录"""
    try:
        response = requests.get('http://127.0.0.1:26000/api/recordings?page=1&page_size=50')
        if response.status_code == 200:
            data = response.json()
            recordings = data.get('recordings', [])
            return recordings
        else:
            print(f'获取录音列表失败: {response.status_code}')
            print(response.text)
            return []
    except Exception as e:
        print(f'请求失败: {e}')
        print('请确保FastAPI服务正在运行在26000端口')
        return []

def delete_recording(recording_id):
    """删除指定的录音记录"""
    try:
        response = requests.delete(f'http://127.0.0.1:26000/api/recordings/{recording_id}')
        if response.status_code == 200:
            print(f'✅ 成功删除录音: {recording_id}')
            return True
        else:
            print(f'❌ 删除录音失败: {recording_id}, 状态码: {response.status_code}')
            print(response.text)
            return False
    except Exception as e:
        print(f'❌ 删除录音时出错: {recording_id}, 错误: {e}')
        return False

def main():
    print('🧹 开始清理录音记录...')
    print('📡 连接到 FastAPI 服务 (端口: 26000)')
    
    # 获取所有录音记录
    recordings = get_recordings()
    
    if not recordings:
        print('❌ 没有找到录音记录或服务连接失败')
        print('💡 请确保已启动 FastAPI 服务: python start_with_ai.py')
        return
    
    total_count = len(recordings)
    print(f'📊 总共找到 {total_count} 条录音记录')
    
    # 按创建时间排序，最新的在前面
    recordings_sorted = sorted(recordings, key=lambda x: x.get('createdAt', ''), reverse=True)
    
    # 显示所有录音记录信息
    print('\n📋 当前录音记录列表:')
    for i, rec in enumerate(recordings_sorted, 1):
        title = rec.get('title', '无标题')
        created_at = rec.get('createdAt', '')
        recording_id = rec.get('id', '')
        duration = rec.get('duration', 0)
        print(f'  {i}. ID: {recording_id[:8]}..., 标题: {title}, 时长: {duration}s, 创建时间: {created_at}')
    
    if total_count <= 2:
        print('✅ 录音记录不超过2条，无需清理')
        return
    
    # 保留前两条，删除其余的
    keep_count = 2
    recordings_to_keep = recordings_sorted[:keep_count]
    recordings_to_delete = recordings_sorted[keep_count:]
    
    print(f'\n🛡️ 将保留最新的 {keep_count} 条记录:')
    for i, rec in enumerate(recordings_to_keep, 1):
        title = rec.get('title', '无标题')
        print(f'  {i}. {rec.get("id", "")[:8]}... - {title}')
    
    print(f'\n🗑️ 将删除以下 {len(recordings_to_delete)} 条记录:')
    for i, rec in enumerate(recordings_to_delete, 1):
        title = rec.get('title', '无标题')
        print(f'  {i}. {rec.get("id", "")[:8]}... - {title}')
    
    # 确认删除
    print(f'\n⚠️ 警告：此操作将永久删除 {len(recordings_to_delete)} 条录音记录及其相关数据！')
    confirm = input(f'确认删除这 {len(recordings_to_delete)} 条记录吗？输入 "yes" 确认: ')
    if confirm.lower() != 'yes':
        print('❌ 操作已取消')
        return
    
    # 执行删除操作
    print('\n🔄 开始删除录音记录...')
    success_count = 0
    fail_count = 0
    
    for i, rec in enumerate(recordings_to_delete, 1):
        recording_id = rec.get('id', '')
        title = rec.get('title', '无标题')
        if recording_id:
            print(f'  删除进度: {i}/{len(recordings_to_delete)} - {title}')
            if delete_recording(recording_id):
                success_count += 1
            else:
                fail_count += 1
        else:
            print(f'❌ 录音记录缺少ID，跳过')
            fail_count += 1
    
    print(f'\n🎉 清理完成！')
    print(f'✅ 成功删除: {success_count} 条')
    print(f'❌ 删除失败: {fail_count} 条')
    print(f'📝 保留记录: {keep_count} 条')
    
    if success_count > 0:
        print('\n💡 建议刷新前端页面查看最新数据')

if __name__ == '__main__':
    main()