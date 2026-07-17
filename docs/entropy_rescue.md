# Public-State Entropy Rescue

## 动机

512-bit Qwen 实验的失败轨迹平均熵只有 0.56-0.66 bit/token，并伴随重复段落。继续增加
token 预算会产生更长但信息量很低的文本。Entropy Rescue 使用公开状态检测连续低熵，达到
patience 后把 temperature 从基础值提高到公开救援值。

## 控制器

```text
base_distribution <- softmax(logits / base_temperature)
base_entropy <- H(base_distribution)
if base_entropy < entropy_floor:
    low_entropy_streak += 1
else:
    low_entropy_streak = 0
if low_entropy_streak >= patience:
    distribution <- softmax(logits / rescue_temperature)
else:
    distribution <- base_distribution
```

输入只包含公开模型输出、公开阈值和公开连续计数，不读取 secret bits。编码方和解码方沿同一
token 前缀重放相同控制器。每步记录基础熵、有效 temperature、救援状态和连续低熵长度。

## 安全边界

该方法保持 SparSamp/RRC 相对“自适应后的分布”进行采样，但不保持相对固定 temperature
基线的原始分布。救援激活位置和 temperature 变化可能被检测，因此必须比较：

- adaptive native generation；
- adaptive SparSamp/RRC；
- fixed-temperature native/stego。

只有 adaptive native 与 adaptive stego 不可区分时，才能讨论条件安全；不能沿用固定分布下
的零 KL 结论。当前版本是机制 pilot，不是最终安全声明。
