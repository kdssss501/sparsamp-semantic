# R026：认证微帧与局部擦除

## 研究问题

R025 的跨精度失败具有全局传播性：任一关键概率边界漂移都可能让稀疏区间塌缩，后续消息状态随之失效。R026 检验固定 token 窗口能否把这种失败限制在单个窗口，并通过认证把错误符号转为 Reed-Solomon 可处理的擦除。

## 机制

- 每个窗口固定 `W` 个 token，窗口开始时重置稀疏区间；
- PRF 以 `window_index` 做域分离；
- 每个 codeword 符号附加截断 HMAC，认证失败不输出错误字节，只报告擦除；
- 微帧在嵌入前使用独立 HMAC 流掩码，避免直接暴露 HMAC/RS 冗余结构；
- 外层纠错调用 `reedsolo 1.7.0`，不在项目内手写 RS；
- singleton 提前完成后，窗口剩余位置使用模型原生采样填充，保持公开边界固定。

完整数学合同见 `docs/microframe_r026.md`。

## 预注册假设与门槛

H1（正确性）：相同模型合同下，所有完成且认证通过的窗口恢复原符号，完整消息恢复率为 100%。

H2（隔离性）：破坏一个窗口后，解码器仍处理后续窗口，前一窗口的区间状态不会进入后一窗口。

H3（纠错性）：若擦除字节数不超过 RS parity 字节数，外层解码恢复原 payload。

GPU-PARTIAL-GO：FP32→FP16 的完整消息成功率高于 R025 Decimal `2/6`，且同精度控制为 `6/6`；同时报告容量代价。

GPU-GO：至少 `5/6` 跨精度完整恢复，aggregate BER `<=0.10`，同精度 `6/6`，并且相对无 RS 微帧有明确恢复增益。

NO-GO：同精度失败，或 RS 版本未提高完整消息恢复且 bits/token 下降超过 50%。

## 已完成验证

- 新增 5 项 R026 单元测试，覆盖互逆、固定窗口截断、认证擦除、窗口隔离和 RS 恢复；全部通过。
- 项目全量 Pytest 通过（128 项）。
- 全项目 Ruff 通过。
- Mock 审计：2 字节 payload、2 parity bytes、1 byte/window、8-bit tag、12 tokens/window；4/4 窗口完成并认证，payload 完整恢复。净 payload bits/token 为 `16/48 = 0.3333`，含奇偶位的 codeword bits/token 为 `32/48 = 0.6667`。
- GPT-2 FP32 同精度 smoke：4/4 窗口完成认证并完整恢复；净 payload bits/token 为 `0.3333`。该结果只验证控制路径，不是跨精度增益。
- GPT-2 FP32→FP16、8-bit tag smoke：0/4 窗口可用；1 个区间塌缩、3 个认证失败，形成 4 个字节擦除，超过 2-byte RS 纠错能力，消息恢复失败。
- 诊断性 4-bit tag（12-bit 微帧）仍为 0/4 窗口可用；2 个区间塌缩、2 个认证失败。缩短认证位没有改善该轨迹，且 4-bit tag 本身不满足安全配置要求。
- 受控破坏首窗口时，该窗口被认证层转为擦除，后续窗口继续解码，RS 恢复 `b"AB"`。

## 当前结论

R026 达到 `GO-MECHANISM / NO-GO-CROSS-PRECISION-SMOKE`：错误局部化和擦除恢复在确定性 Mock 合同下成立，GPT-2 FP32 同精度控制通过；但首条 FP32→FP16 轨迹的窗口擦除率为 100%，没有达到 GPU-PARTIAL-GO。增加 RS 冗余无法在全部窗口失效时恢复消息。

当前不能声称：跨精度成功率提高、优于原论文、保持固定密钥下零 KLD、可推广到 Qwen 中文生成。HMAC 掩码只给出 PRF 假设下的计算不可区分性；RS 和认证冗余会降低净 payload bits/token。该负结果指向 R027：在 top-p 截断之前稳定 logits/支持边界，再让微帧处理剩余的稀疏错误。

## ARIS 消融顺序

1. 组件消融：monolithic Decimal、微帧无认证/无 RS、认证微帧无 RS、认证微帧 + RS。
2. 固定窗口：`W={8,12,16}`，先用 3 prompts x 2 seeds；不同时改变 tag 和 parity。
3. 认证位：`a={8,16}`，测未检测错误率与容量代价；4-bit 仅作故障注入，不作安全配置。
4. RS 冗余：`parity_bytes={0,2,4}`，主指标为完整消息成功率、BER、擦除字节数和净 payload bits/token。
5. 仅在 GPT-2 FP32→FP16 达到 PARTIAL-GO 后，迁移到 Qwen FP32→FP16/FP16→FP16 和中文 prompt。

不优先扫描水填充 headroom；R025 已表明逐步合同提升不等价于消息级提升。第一轮总计 4 个机制变体，预计 24 条编码轨迹，复用解码轨迹，先以 GPT-2 控制计算成本。

## 复现命令

```powershell
$env:PYTHONPATH='.;src'
uv run --no-sync python -m pytest tests\test_microframe.py -q
uv run --no-sync python scripts\audit_microframe.py `
  --provider mock --payload-hex 4142 --window-tokens 12 `
  --symbol-bytes 1 --auth-tag-bits 8 --parity-bytes 2 `
  --output outputs\R026_microframe_mock.json
```

本地 HF 同精度 smoke 可将 `--provider mock` 替换为：

```powershell
--provider hf --model models\gpt2 --device cuda --dtype float32
```
