# pairwise-audiokit

## 题面（可直接粘贴）

语音网关改成分片重采样后语速抖动：分片处理与整段结果不同、flush 后还能继续喂数据、延迟估计每段都变导致时间戳漂移。audiokit/core.py 是核心，tests/test_core.py 15 个红。要修的是：分片与整段逐样本一致；常量信号不变；flush 后再 process 抛 ValueError；reset 后可复现；延迟恒定；非法采样率抛 ValueError；两个实例互不影响。

## 运行方式

```bash
python -m pytest tests -q
```

初始结果应为 `15 failed`（全部因 `NotImplementedError` 失败，无 collection error）。

## 字段

- 所属领域：游戏、图形与多媒体
- 子方向：音视频处理
- 任务类型：Bugfix
- 语言/框架：Python 3, pytest
- 环境可复现等级：无外部依赖
