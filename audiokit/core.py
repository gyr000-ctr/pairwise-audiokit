"""audiokit 核心 API：分片确定性的流式重采样器。

设计要点
--------
- 用 ``gcd`` 把采样率比约成最简整数比 ``p/q``，输出位置由全局整数相位
  累加器决定。相位只依赖“已经喂入的样本总数”，与分片边界无关，因此
  逐样本分片与整段处理得到完全一致的输出。
- 状态仅保存最近两个输入样本及其全局下标，不缓存整段输入，内存占用恒定。
- ``flush`` 后流结束，再调用 ``process`` 抛出 ``ValueError``；``reset``
  可把状态恢复到构造后的初始状态，结果可复现。
- 延迟为固定值，不随处理进度变化。
"""

from math import gcd

__all__ = ["Resampler"]

# 固定延迟（输入样本数）：线性插值重采样引入的一帧算法延迟。
_LATENCY = 1


def _check_rate(value, name):
    # bool 是 int 的子类，采样率不接受布尔值。
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be a positive integer, got {value!r}")


class Resampler:
    def __init__(self, src_rate, dst_rate):
        """构造重采样器。

        Parameters
        ----------
        src_rate, dst_rate : int
            源/目标采样率，必须为正整数，否则抛出 ``ValueError``。
        """
        _check_rate(src_rate, "src_rate")
        _check_rate(dst_rate, "dst_rate")

        self._src_rate = src_rate
        self._dst_rate = dst_rate

        g = gcd(src_rate, dst_rate)
        self._p = dst_rate // g  # 输出端步进（分子）
        self._q = src_rate // g  # 输入端步进（分母）

        self.reset()

    def reset(self):
        """重置状态：等价于一个全新的重采样器，历史数据全部丢弃。"""
        # 已喂入的输入样本总数（全局下标上界）。
        self._n_in = 0
        # 已产出的输出样本总数。
        self._n_out = 0
        # 最近两个输入样本：下标 -> 值，最多保留两项。
        self._prev = {}
        # flush 之后流结束，禁止继续喂数据。
        self._finished = False
        return None

    def process(self, samples):
        """处理一段样本，返回当前可产出的输出样本列表。

        流式处理时，只有当插值所需的两个相邻输入样本都已到达时才产出；
        末尾尚未闭合的部分保留到 :meth:`flush`。
        """
        if self._finished:
            raise ValueError("cannot process() after flush(); call reset() first")

        out = []
        for v in samples:
            self._add_sample(float(v))
            out.extend(self._drain(clamp=False))
        return out

    def flush(self):
        """结束输入流，返回剩余样本。

        末尾超出最后一个输入样本位置的输出按边界样本钳制（不做外推）。
        flush 可重复调用，第二次起返回空列表。
        """
        if self._finished:
            return []
        self._finished = True
        return self._drain(clamp=True)

    def latency(self):
        """返回固定延迟（输入样本数），与处理进度无关。"""
        return _LATENCY

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------

    def _add_sample(self, value):
        idx = self._n_in
        self._n_in = idx + 1
        self._prev[idx] = value
        # 只保留最近两个下标，更早的样本永远不会再被插值访问。
        if len(self._prev) > 2:
            stale = min(self._prev)
            del self._prev[stale]

    def _at(self, idx):
        """取全局下标 ``idx`` 处的输入样本；越界时按边界钳制。

        正常路径下 ``idx`` 总在已到达样本范围内（``idx`` 由非负相位
        计算得到，不会为负）；钳制只在 flush 的边界输出时发生。
        """
        if idx in self._prev:
            return self._prev[idx]
        # idx 超过已到达范围：钳到最后一个已到达样本。
        return self._prev[max(self._prev)]

    def _drain(self, clamp):
        out = []
        p, q = self._p, self._q

        # 总输出样本数由输入总长度与采样率比唯一确定：floor(N * p / q)。
        total = (self._n_in * p) // q

        while self._n_out < total:
            m = self._n_out
            # 第 m 个输出对应的输入位置（定点数，分母为 q）。
            pos_num = m * p
            idx = pos_num // q
            frac_num = pos_num - idx * q  # 0..q-1

            if not clamp:
                # 流式阶段：插值需要 idx 与 idx+1 两个样本都已到达，
                # 否则留待后续 process 或 flush 处理。
                if idx + 1 >= self._n_in:
                    break

            v0 = self._at(idx)
            v1 = self._at(idx + 1)
            value = v0 + (v1 - v0) * (frac_num / q)
            out.append(value)
            self._n_out = m + 1

        return out
