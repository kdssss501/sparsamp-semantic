# Stage 3 模拟同行评审检查点

## 结论

**Major Revision（大修）**。这不是拒稿：五位评审都没有在 D1-D3 强制维度给出 `block`，说明当前同机、目标特定的核心结果可以保留。大修由冻结合同机械触发：5/5 评审均有至少两个强制维度 `warn`，且 EIC 与 Devil's Advocate 对 D4 广泛意义给出 `block`。

## 当前最强结论

在固定 Qwen2.5-1.5B、固定 tokenizer、固定 RTX 3060 软件栈和已知 FP16/BF16 目标环境下，完整 correction manifest 能恢复全部 60 条参考 token 轨迹；经验贡献是平均仅 2.16% 的 token 位置需要修正，而不是“60/60”本身。

## 当前不能写成的结论

- 不能写成跨硬件通用确定性。
- 不能写成保持原模型分布或零 KL。
- 不能写成语义质量等同于原生 Qwen。
- 不能写成已证明优于普通 delta log、checkpoint 或全 token trace。
- 不能以当前证据声称达到 Nature Communications 的广泛意义门槛。

## 下一轮最小闭环

1. 独立物理 GPU 上重放冻结 bundle。
2. 同一成本边界下补 full trace、native delta、checkpoint 三个基线。
3. 单独量化 integer apportionment 的分布误差。
4. 冻结小规模 (q,T,B,k) 敏感性实验。
5. 选择期刊路线：补第二模型冲广泛期刊，或收窄定位投 TMLR/MLST。

Stage 3 不修改主稿。收到作者明确确认后，才能进入 Stage 4 修订。
