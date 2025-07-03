#!/usr/bin/env python3
"""
测试发言人API接口
"""

import requests
import json
from loguru import logger

# API基础URL
BASE_URL = "http://localhost:26000"

def test_frequent_speakers_api():
    """测试常用发言人API"""
    logger.info("开始测试常用发言人API...")
    
    try:
        # 1. 获取常用发言人列表
        response = requests.get(f"{BASE_URL}/api/speakers/frequent")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ 获取常用发言人: {data['total']} 个")
            for speaker in data['data']:
                logger.info(f"  - {speaker['name']} (使用次数: {speaker['useCount']})")
        else:
            logger.error(f"❌ 获取常用发言人失败: {response.status_code}")
            return False
        
        # 2. 添加新的常用发言人
        new_speaker = {
            "name": "API测试发言人",
            "color": "#00ff00"
        }
        response = requests.post(f"{BASE_URL}/api/speakers/frequent", json=new_speaker)
        if response.status_code == 200:
            speaker_data = response.json()
            logger.info(f"✅ 添加常用发言人成功: {speaker_data['data']['name']}")
            speaker_id = speaker_data['data']['id']
        else:
            logger.error(f"❌ 添加常用发言人失败: {response.status_code}")
            return False
        
        # 3. 更新常用发言人
        update_data = {
            "name": "API测试发言人(已更新)",
            "color": "#ff00ff"
        }
        response = requests.put(f"{BASE_URL}/api/speakers/frequent/{speaker_id}", json=update_data)
        if response.status_code == 200:
            logger.info("✅ 更新常用发言人成功")
        else:
            logger.error(f"❌ 更新常用发言人失败: {response.status_code}")
            return False
        
        # 4. 删除常用发言人
        response = requests.delete(f"{BASE_URL}/api/speakers/frequent/{speaker_id}")
        if response.status_code == 200:
            logger.info("✅ 删除常用发言人成功")
        else:
            logger.error(f"❌ 删除常用发言人失败: {response.status_code}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 常用发言人API测试异常: {str(e)}")
        return False

def test_speaker_update_api():
    """测试发言人更新API"""
    logger.info("开始测试发言人更新API...")
    
    try:
        # 首先获取一个录音ID（用于测试）
        response = requests.get(f"{BASE_URL}/api/recordings?page=1&page_size=1")
        if response.status_code == 200:
            recordings = response.json()
            if recordings['recordings']:
                recording_id = recordings['recordings'][0]['id']
                logger.info(f"使用录音ID进行测试: {recording_id}")
                
                # 测试更新录音中的发言人
                update_data = {
                    "new_name": "测试更新的发言人",
                    "setting_type": "single"
                }
                response = requests.post(
                    f"{BASE_URL}/api/recordings/{recording_id}/speakers/发言人1/update",
                    json=update_data
                )
                
                if response.status_code == 200:
                    logger.info("✅ 更新录音中发言人成功")
                    
                    # 获取设置日志
                    response = requests.get(f"{BASE_URL}/api/recordings/{recording_id}/speakers/settings-log")
                    if response.status_code == 200:
                        logs = response.json()
                        logger.info(f"✅ 获取设置日志成功: {logs['total']} 条")
                    else:
                        logger.error(f"❌ 获取设置日志失败: {response.status_code}")
                        return False
                else:
                    logger.error(f"❌ 更新录音中发言人失败: {response.status_code}")
                    return False
            else:
                logger.warning("⚠️ 没有录音数据，跳过发言人更新测试")
                return True
        else:
            logger.error(f"❌ 获取录音列表失败: {response.status_code}")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 发言人更新API测试异常: {str(e)}")
        return False

def test_all_apis():
    """测试所有API接口"""
    logger.info("🚀 开始测试所有发言人API接口...")
    
    # 测试常用发言人API
    if not test_frequent_speakers_api():
        logger.error("❌ 常用发言人API测试失败")
        return False
    
    # 测试发言人更新API
    if not test_speaker_update_api():
        logger.error("❌ 发言人更新API测试失败")
        return False
    
    logger.success("🎉 所有发言人API测试通过!")
    return True

if __name__ == "__main__":
    # 配置日志
    logger.add("api_test.log", rotation="10 MB", level="INFO")
    
    print("请确保后端服务已启动 (python main.py)")
    input("按回车键开始测试...")
    
    test_all_apis() 