# Portable Precision Context

## 目的

SparSamp 的 HMAC 随机流由共享密钥和 Provider `context_id` 派生。历史严格模式把 `dtype` 与 4-bit 加载状态写入 context，因此 FP32 编码端和 FP16 解码端即使得到相同概率合同，也会使用不同随机流。

R025 增加显式上下文模式：

- `strict`：保留历史行为，把 dtype 和量化加载状态写入 context；
- `portable`：用公开常量 `portable-precision` 替代这些执行精度字段。

默认仍为 `strict`，旧 artifact 的 context ID 不变。

## 合同

Portable 模式只排除以下执行实现字段：

- `dtype`；
- `load_in_4bit`。

以下字段仍进入 context：模型路径/revision、top-p、top-k、温度、system prompt、用户 prompt 和非默认候选顺序。编码端和解码端必须显式共享 `precision_context="portable"`。

## 安全边界

Portable context 不声称不同精度模型等价。它只保证在其他公开配置相同的条件下使用同一 PRF 流，把概率分布差异留给概率合同处理。

如果 tokenizer、模型 revision、候选顺序或采样参数不同，context 仍应不同。生产默认严格模式避免用户无意中把不同执行环境视为同一合同。

## R025 验证

单元测试确认 portable 模式下 FP32/FP16 context ID 相同、strict 模式下不同。消息级实验中所有 24 条 FP32 同精度控制均成功，且 FP16 端未出现 PRF context 配置错误。Portable context 是跨精度研究的必要控制，不是概率鲁棒性改进本身。
