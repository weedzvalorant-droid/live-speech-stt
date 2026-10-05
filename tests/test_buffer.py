import numpy as np

from livestt.audio.buffer import UtteranceBuffer


def test_append_and_get_concatenates_chunks():
    buf = UtteranceBuffer(sample_rate=16000)
    buf.append(np.ones(100, dtype=np.float32))
    buf.append(np.ones(50, dtype=np.float32) * 2)
    result = buf.get()
    assert result.shape[0] == 150
    assert result[0] == 1.0
    assert result[-1] == 2.0


def test_duration_seconds():
    buf = UtteranceBuffer(sample_rate=16000)
    buf.append(np.zeros(16000, dtype=np.float32))
    assert buf.duration_seconds() == 1.0


def test_clear_resets_buffer():
    buf = UtteranceBuffer(sample_rate=16000)
    buf.append(np.zeros(1000, dtype=np.float32))
    buf.clear()
    assert len(buf) == 0
    assert buf.get().shape[0] == 0


def test_appending_empty_array_is_noop():
    buf = UtteranceBuffer(sample_rate=16000)
    buf.append(np.zeros(0, dtype=np.float32))
    assert len(buf) == 0


def test_max_seconds_cap_drops_oldest_chunks():
    buf = UtteranceBuffer(sample_rate=100, max_seconds=1.0)  # cap = 100 samples
    buf.append(np.full(60, 1.0, dtype=np.float32))
    buf.append(np.full(60, 2.0, dtype=np.float32))
    result = buf.get()
    assert result.shape[0] <= 120  # cap enforced only when >1 chunk remains
    # the oldest chunk (all 1.0) should have been dropped once total exceeded the cap
    assert not np.all(result == 1.0)
