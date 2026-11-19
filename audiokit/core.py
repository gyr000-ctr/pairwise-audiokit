"""audiokit 核心 API（初始未实现）。"""


class Resampler:
    def __init__(self, src_rate, dst_rate):
        """构造重采样器"""
        raise NotImplementedError

    def process(self, samples):
        """处理一段样本"""
        raise NotImplementedError

    def flush(self):
        """结束并返回剩余样本"""
        raise NotImplementedError

    def latency(self):
        """返回固定延迟（样本数）"""
        raise NotImplementedError

    def reset(self):
        """重置状态"""
        raise NotImplementedError
