#!/usr/bin/env python3
"""
音频阈值配置测试脚本
验证修复后的音频质量检测阈值是否合理
"""

import numpy as np
from config import audio_config, quality_config

def test_audio_thresholds():
    """测试音频阈值配置"""
    print("🔊 音频阈值配置测试")
    print("=" * 50)
    
    # 显示当前配置
    print("📊 当前音频质量配置:")
    print(f"   最低能量阈值: {audio_config.MIN_ENERGY_THRESHOLD}")
    print(f"   零交叉率阈值: {audio_config.ZERO_CROSSING_THRESHOLD}")
    print(f"   信噪比阈值: {audio_config.SNR_THRESHOLD} dB")
    
    # 模拟几种类型的音频片段
    sample_rate = 16000
    duration = 3.0  # 3秒
    samples = int(sample_rate * duration)
    
    test_cases = [
        ("正常语音信号", generate_speech_like_audio(samples)),
        ("低能量语音", generate_speech_like_audio(samples) * 0.1),
        ("噪音信号", np.random.random(samples) * 0.01),
        ("静音", np.zeros(samples)),
        ("高噪音", np.random.random(samples) * 0.5),
    ]
    
    print("\n🧪 测试结果:")
    
    for name, audio in test_cases:
        result = test_audio_quality(audio, name)
        status = "✅ 通过" if result["valid"] else "❌ 被过滤"
        print(f"   {name}: {status}")
        print(f"      能量: {result['energy']:.6f}")
        print(f"      零交叉率: {result['zcr']:.4f}")
        print(f"      动态范围: {result['std']:.6f}")
        if not result["valid"]:
            print(f"      过滤原因: {result['reason']}")
        print()

def generate_speech_like_audio(samples):
    """生成类似语音的测试音频"""
    # 生成带有基频和谐波的信号，模拟语音
    t = np.linspace(0, samples/16000, samples)
    
    # 基频（模拟声带振动）
    f0 = 120  # Hz
    signal = 0.3 * np.sin(2 * np.pi * f0 * t)
    
    # 添加谐波
    for harmonic in [2, 3, 4]:
        amplitude = 0.1 / harmonic
        signal += amplitude * np.sin(2 * np.pi * f0 * harmonic * t)
    
    # 添加一些随机变化（模拟语音的自然变化）
    noise = np.random.random(samples) * 0.02 - 0.01
    signal += noise
    
    # 添加包络（模拟语音的音量变化）
    envelope = np.abs(np.sin(2 * np.pi * 0.5 * t)) + 0.1
    signal *= envelope
    
    return signal.astype(np.float32)

def test_audio_quality(chunk, name):
    """测试音频质量（复制录音服务中的逻辑）"""
    result = {"valid": True, "reason": "", "energy": 0, "zcr": 0, "std": 0}
    
    # 1. 检查时长
    duration = len(chunk) / 16000
    if duration < audio_config.MIN_CHUNK_DURATION:
        result["valid"] = False
        result["reason"] = f"时长太短({duration:.2f}s)"
        return result
    
    # 2. 检查音频能量
    audio_energy = np.mean(np.abs(chunk))
    result["energy"] = audio_energy
    if audio_energy < audio_config.MIN_ENERGY_THRESHOLD:
        result["valid"] = False
        result["reason"] = f"能量太低({audio_energy:.6f})"
        return result
    
    # 3. 检查动态范围
    audio_std = np.std(chunk)
    result["std"] = audio_std
    if audio_std < audio_config.MIN_ENERGY_THRESHOLD:
        result["valid"] = False
        result["reason"] = f"动态范围太小({audio_std:.6f})"
        return result
    
    # 4. 检查峰值
    max_amplitude = np.max(np.abs(chunk))
    if max_amplitude > 0.99:
        result["valid"] = False
        result["reason"] = f"可能削波(峰值:{max_amplitude:.3f})"
        return result
    
    # 5. 检查零交叉率
    zero_crossings = np.sum(np.diff(np.signbit(chunk)))
    zcr = zero_crossings / len(chunk)
    result["zcr"] = zcr
    if zcr > audio_config.ZERO_CROSSING_THRESHOLD:
        result["valid"] = False
        result["reason"] = f"零交叉率过高({zcr:.3f})"
        return result
    
    # 6. 检查频谱
    fft = np.fft.fft(chunk)
    magnitude = np.abs(fft)
    total_energy = np.sum(magnitude)
    
    if total_energy == 0:
        result["valid"] = False
        result["reason"] = "频谱能量为零"
        return result
    
    # 检查低频能量占比
    low_freq_energy = np.sum(magnitude[:len(magnitude)//4])
    low_freq_ratio = low_freq_energy / total_energy
    
    if low_freq_ratio < 0.1:
        result["valid"] = False
        result["reason"] = f"低频能量比例太小({low_freq_ratio:.3f})"
        return result
    
    return result

def main():
    test_audio_thresholds()
    
    print("💡 建议:")
    print("   如果正常语音信号被过滤，需要进一步降低阈值")
    print("   如果噪音信号没有被过滤，需要提高阈值")
    print("   目标：让正常语音通过，过滤明显的噪音和静音")

if __name__ == "__main__":
    main() 