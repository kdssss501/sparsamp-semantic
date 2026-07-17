# R019 Verified-RRC 数学正确性审计

日期：2026-07-17

## 审计对象

- Yan 与 Murawaki, *Efficient Provably Secure Linguistic Steganography via Range Coding*,
  ACL 2026，Algorithm 3/4、Section 5、Appendix B。
- 本地规范 PDF：`.artifacts/papers/range-coding-acl2026.pdf`。
- PDF SHA-256：`2117F109BC21037D691B1FCE4B37E00542928DB5F21BA6235ABE713CBEF620D4`。
- 本项目 clean-room 实现：`src/sparsamp_semantic/rrc.py`。
- 精确审计实现：`src/sparsamp_semantic/rrc_theory.py`。

本审计只评价论文公开算法在本文采用的形式化下是否支持对应数学命题，不推断未公开实现，
也不把有限测试升级为形式化验证。

## 结论 1：局部停止条件不是精确恢复的充分条件

论文 Algorithm 3 在

```text
-1/2 < midpoint(I^t) - d^t <= 1/2
```

时停止。精确两步有理数反例为：

```text
M=8, m=3, I^-1=[0,8), o_0=0, I^0=[3,5),
o_1=1/2, d^1=4, I^1=[3,9/2), midpoint=15/4.
```

局部误差为 `-1/4`，满足停止条件；Algorithm 4 反向重放却得到 `19/4`，
`round_half_down(19/4)=5 != 3`。根因是逆模旋转跨越线性切点，圆周距离保持不代表普通
线性误差保持。

该问题不是连续偏移中的零概率单点。对

```text
o_0 in [0,1/64], o_1 in [15/32,17/32]
```

整个矩形，局部条件均成立且解码恒为 5。独立连续均匀偏移落入该区域的概率为
`1/1024`。

## 结论 2：`-log Z` 是反向 KL，不是论文安全指标方向

令完整分布为 `P`，top-p 保留支持为 `S`，保留质量为 `Z`，条件分布为 `Q=P(.|S)`。
精确恒等式是

```text
KL(Q||P) = -log Z.
```

论文 Section 2.3、2.4、6.2 使用的是 `KL(P_cover||P_stego)`。若 cover 为完整 `P`、stego
为截断 `Q` 且 `Z<1`，则支持外存在 `P_i>0,Q_i=0`，所以

```text
KL(P||Q) = +infinity.
```

因此项目原有 `truncation_kl_nats=-log(source_mass)` 只能标为反向 KL。要讨论理想零 KL，
正常生成 baseline 必须使用完全相同的 temperature、top-k、top-p，令 cover 本身就是 `Q`。
若 codec 再把 `Q` 量化为 `R`，论文方向应报告 `KL(Q||R)`；反向分解

```text
KL(R||P) = -log Z + KL(R||Q)
```

仍然成立，但不能替代论文方向指标。

## 结论 3：逐步分布匹配不保证变长全文分布匹配

论文 Appendix B.3 Step 2 从“活动状态下每步 token 条件分布匹配”推向“随机停止后的全文
与正常生成不可区分”，并把随机停止时间 `T` 与固定 `L=E[T]` 的正常生成比较。该推导遗漏
了停止 hazard；两种过程也不一定具有相同的长度样本空间。

精确公平 bit 反例：首 bit 为 0 时停止，否则再生成一个公平 bit。stego 分布为

```text
Pr(0)=1/2, Pr(10)=1/4, Pr(11)=1/4.
```

即使 cover 具有完全相同的长度边缘分布，再独立生成公平 bit，也有
`Pr_cover(0)=1/4`。事件“输出为 0”的区分优势为 `1/4`，完整序列分布的总变差距离为
`1/2`。

因此 RRC、Verified-RRC 和语义句号收尾都必须单独报告长度通道。一个充分修复是规定公开
固定总长度 `N`，嵌入完成后继续按同一 cover 分布生成到 `N`；此时若每一步给定公开历史的
条件 token 分布都等于 cover，固定长度全文分布由链式法则保持一致。

## 已证明的 Verified-RRC 边界

若编码器和解码器确定性重建相同概率区间、偏移、token 序列和舍入规则，且发送端仅在完整
执行公开 Algorithm 4 后恢复原消息时输出，则接收端必然恢复同一消息。这是成功返回时正确
的 safety 定理。

当前没有证明：

- 对任意语言模型、消息和偏移必然有限终止；
- Decimal 精度启发式永不改变区间选择或最终舍入；
- top-p、概率量化、熵救援后的分布相对完整 softmax 保持论文方向零 KL；
- 数据相关停止的变长文本与正常生成全文不可区分。

## 下一版理论驱动实现

1. 固定公开总长度，payload 完成后按同配置 cover 分布填充，消除直接停止长度通道。
2. 将概率映射为固定总频数 `D` 的公开整数表，用整数区间运算替代 Decimal 正确性启发式。
3. 同时报告 `KL(Q||R)`、`KL(R||Q)`、固定长度全文 steganalysis 和消息恢复率。
4. 保留 `IncompleteEncodeError`；在有限终止定理完成前不承诺任意输入必定完成。

## 可复现验证

```powershell
python scripts/verify_rrc_theory.py
pytest tests/test_rrc_theory.py tests/test_rrc.py -q
pytest -q
```

当前结果：理论/RRC 定向测试通过，全项目 75 个测试通过；存在一条 FastAPI TestClient 的
上游弃用警告，不影响本次数学审计。
