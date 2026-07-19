# R026：固定窗口认证微帧

## 目标

R025 暴露的主要失败模式是稀疏区间在一个精度漂移位置塌缩，随后污染整条消息。R026 将消息划分为固定公开窗口，每个窗口独立初始化区间和 PRF 域。窗口没有在 `W` 个 token 内到达 singleton 时只记为擦除，不把不完整区间带入下一窗口。

## 合同

设窗口索引为 `j`，窗口长度为 `W`，每个符号为 `s` 字节。先对 payload 做 Reed-Solomon 编码得到 codeword `C`，按 `s` 字节切分为 `C_j`。认证值为

\[
  T_j = \operatorname{Trunc}_a(\operatorname{HMAC}_K(\text{context}\|j\|C_j)).
\]

令 `X_j = C_j || T_j`，使用独立域 `frame || j` 的 HMAC 扩展流产生同长度掩码 `M_j`，实际嵌入的整数为 `K_j = X_j xor M_j`。因此在 PRF 理想化假设下，观察者看到的微帧值计算上接近均匀；不能把该结论写成固定密钥下的信息论零 KLD。

编码器在窗口内使用 `domain = window || j` 的随机数推进 SparSamp 区间。达到 `n_m=1` 后，剩余 token 采用模型原生采样并仍计入该窗口。解码器只在同一窗口内反演；窗口结束时：

- 未达到 singleton：擦除；
- 达到 singleton 但 HMAC 不匹配：擦除；
- 认证通过：输出 `C_j`。

若有 `e` 个错误符号和 `s` 个擦除符号，Reed-Solomon 的可纠正条件是 `2e+s <= parity_bytes`。本实现只产生认证失败擦除，不把未经认证的错误字节交给 RS；认证截断长度为 `a` 时，随机错误被误接受的单窗口概率上界为 `2^-a`（在 PRF/独立错误假设下）。

## 伪代码

```text
for window j:
    X = codeword_symbol[j] || HMAC_tag(j, codeword_symbol[j])
    K = X xor PRF_mask(j)
    reset n_m, k_m from K
    for local_step = 0 .. W-1:
        observe Q_t and r = PRF(window=j, step=local_step)
        if interval active: perform one sparse interval update
        else: append native model sample
    if interval never reached singleton: mark erasure

decode each window independently, authenticate recovered symbol,
then call a mature RS decoder with authenticated windows as symbols and
all failed windows as erasures.
```

## 复杂度与边界

设 `m` 个窗口、候选支持大小为 `K_t`。编码/解码时间为 `O(sum_t K_t)`（线性扫描 inverse-CDF），窗口状态空间为 `O(W + b)`，其中 `b = 8s+a`。RS 解码由 `reedsolo` 提供，复杂度和纠错半径由其实现决定。固定窗口会降低可见 bits/token，这是可靠性和容量之间的明确代价，必须与 monolithic SparSamp 分开报告。

R026 的主张范围是“把精度漂移造成的全局失败转化为可认证的局部擦除，并评估外层纠错是否值得其容量代价”，不是“恢复原论文的零失真分布保持”。
