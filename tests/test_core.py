import math
import threading

import pytest

import audiokit

def _raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return True
    return False

def _one_shot(samples, a, b):
    r = audiokit.Resampler(a, b)
    out = r.process(samples)
    return out + r.flush()


def _chunked(samples, a, b, n):
    r = audiokit.Resampler(a, b)
    out = []
    for i in range(0, len(samples), n):
        out += r.process(samples[i:i + n])
    return out + r.flush()


def _same(n):
    s = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
    return _chunked(s, 8000, 12000, n) == _one_shot(s, 8000, 12000)


def _constant():
    out = _one_shot([0.5] * 16, 8000, 16000)
    return all(abs(v - 0.5) < 1e-9 for v in out)


def _length():
    return len(_one_shot([0.0] * 8, 8000, 4000)) == 4


def _flush_then_process():
    r = audiokit.Resampler(8000, 16000)
    r.flush()
    return _raises(lambda: r.process([0.1]))


def _reset_reproduces():
    r = audiokit.Resampler(8000, 16000)
    a = r.process([0.1, 0.2]) + r.flush()
    r.reset()
    return r.process([0.1, 0.2]) + r.flush() == a


def _latency_stable():
    r = audiokit.Resampler(8000, 16000)
    a = r.latency()
    r.process([0.0] * 100)
    return r.latency() == a


def _empty():
    return _one_shot([], 8000, 16000) == []


def _independent():
    a = audiokit.Resampler(8000, 16000)
    b = audiokit.Resampler(8000, 16000)
    return a.process([0.5]) == b.process([0.5])


def _flush_list():
    return isinstance(audiokit.Resampler(8000, 16000).flush(), list)


def _identity():
    s = [0.1, 0.2, 0.3]
    return _one_shot(s, 8000, 8000) == s

CASES = [
        ("split1", lambda: _same(1)),
        ("split3", lambda: _same(3)),
        ("split5", lambda: _same(5)),
        ("constant", lambda: _constant()),
        ("length", lambda: _length()),
        ("bad_rate", lambda: _raises(lambda: audiokit.Resampler(0, 8000))),
        ("flush_then_process", lambda: _flush_then_process()),
        ("reset", lambda: _reset_reproduces()),
        ("latency", lambda: _latency_stable()),
        ("empty", lambda: _empty()),
        ("independent", lambda: _independent()),
        ("flush_list", lambda: _flush_list()),
        ("identity", lambda: _identity()),
        ("negative_rate", lambda: _raises(lambda: audiokit.Resampler(-8000, 8000))),
        ("process_list", lambda: isinstance(audiokit.Resampler(8000, 16000).process([0.1]), list)),
    ]


@pytest.mark.parametrize("name,check", CASES, ids=[c[0] for c in CASES])
def test_spec(name, check):
    assert check() is True
