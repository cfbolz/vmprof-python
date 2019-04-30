import pytest

def coalesce(profiles, factor=1, skew=0):
    print("number of samples", len(profiles))
    print("max depth", max(len(p[0]) for p in profiles))
    if not profiles:
        return []
    output = []
    stack_with_start_times = []
    start_time = profiles[0][1]
    last_time = profiles[-1][1] + 1

    for profile in profiles + [([], last_time)]:
        sampled_stack = profile[0]
        curr_time = profile[1] - start_time

        # find index up to where two consecutive stack samples agree
        minindex = min(len(sampled_stack), len(stack_with_start_times))
        max_matching_index = 0
        if minindex:
            for max_matching_index in range(minindex):
                addr, start = stack_with_start_times[max_matching_index]
                if sampled_stack[max_matching_index] != addr:
                    break
            else:
                max_matching_index += 1
        size_skew = len(stack_with_start_times) - max_matching_index - 1

        # the functions that are on the last sampled stack but not on the
        # current have finished, output them
        for j in range(max_matching_index, len(stack_with_start_times)):
            end = (curr_time - skew * size_skew) * factor
            output.append(stack_with_start_times.pop() + (end, ))
            size_skew -= 1
        assert len(stack_with_start_times) == max_matching_index
        assert size_skew == -1

        # the functions that are new on the current stack have just started
        size_skew = 0
        for j in range(max_matching_index, len(sampled_stack)):
            start = (curr_time + skew * size_skew) * factor
            stack_with_start_times.append((sampled_stack[j], start))
            size_skew += 1
        assert len(stack_with_start_times) == len(sampled_stack)
    output.sort(key=lambda x: (x[1], x[1] - x[2], x[0]))
    return output

def export_json(log, profiles, fn):
    import json
    # example events:
    # { "pid":1, "tid":1, "ts":87705, "dur":956189, "ph":"X", "name":"Jambase", "args":{ "ms":956.2 } },
    # { "pid":1, "tid":1, "ts":128154, "dur":75867, "ph":"X", "name":"SyncTargets", "args":{ "ms":75.9 } },
    # { "pid":1, "tid":1, "ts":546867, "dur":121564, "ph":"X", "name":"DoThings", "args":{ "ms":121.6 } }
    events = []
    result = {"traceEvents": events, "meta_user": "pypy"}
    for event in log:
        start = event[1]
        stop = event[2]
        events.append(dict(ph="X", pid=1, tid=1, ts=start, dur=stop-start, name=event[0], args={"extra": "nope"}))
    # instant events (all the samples):
    # {"name": "OutOfMemory", "ph": "i", "ts": 1234523.3, "pid": 2343, "tid": 2347, "s": "g"}
    s = profiles[0][1]
    for p in profiles:
        events.append(dict(ph="i", pid=1, tid="sample", ts=(p[1] - s) * 0.001, name="sample"))
    with open(fn, "w") as f:
        json.dump(result, f)


def test_coalesce():
    profiles = [([1, 2], 5, 1)]
    r = coalesce(profiles)
    assert r == [(1, 0, 1), (2, 0, 1)]

    profiles = [([1, 2], 1, 1),
                ([1, 2], 2, 1)]
    r = coalesce(profiles)
    assert r == [(1, 0, 2), (2, 0, 2)]

    profiles = [([1, 2], 1, 1),
                ([1, 3], 2, 1)]
    r = coalesce(profiles)
    assert r == [(1, 0, 2), (2, 0, 1), (3, 1, 2)]

    profiles = [([1], 1, 1),
                ([1, 2], 2, 1),
                ([1], 3, 1)]
    r = coalesce(profiles)
    assert r == [(1, 0, 3), (2, 1, 2)]

    profiles = [([1], 1, 1),
                ([1, 2], 2, 1),
                ([3], 3, 1)]
    r = coalesce(profiles)
    assert r == [(1, 0, 2), (2, 1, 2), (3, 2, 3)]

    profiles = [([1], 1, 1),
                ([1, 2], 2, 1),
                ([3, 2], 3, 1)]
    r = coalesce(profiles)
    assert r == [(1, 0, 2), (2, 1, 2), (2, 2, 3), (3, 2, 3)]

def test_larger_steps():
    profiles = [([1], 0, 1),
                ([1, 2], 5, 1),
                ([3], 10, 1)]
    r = coalesce(profiles)
    assert r == [(1, 0, 10), (2, 5, 10), (3, 10, 11)]

def test_even_more():
    profiles = [([1, 2], 0, 1),
                ([1, 2], 10, 1)]
    r = coalesce(profiles)
    assert r == [(1, 0, 11), (2, 0, 11)]

    profiles = [([1], 0, 1),
                ([1, 2, 3, 4, 5], 10, 1),
                ([1, 2, 6], 15, 1),
                ([1, 7, 8], 20, 1)]
    r = coalesce(profiles)
    assert r == [(1, 0, 21), (2, 10, 20), (3, 10, 15), (4, 10, 15),
                 (5, 10, 15), (6, 15, 20), (7, 20, 21), (8, 20, 21)]

def test_skew():
    profiles = [([1], 0, 1),
                ([1, 2, 3, 4], 100, 1),
                ([1, 2], 300, 1)]
    r = coalesce(profiles, skew=1)
    assert r == [(1, 0, 301), (2, 100, 300), (3, 101, 300), (4, 102, 299)]
