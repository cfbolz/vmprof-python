from vmprof.reader import StackSample

def coalesce(profiles, factor=1, skew=0):
    """ This function converts a set of stack samples into an roughly
    approximate flame chart.

    A flame chart is a flame graph where the x-axis is wall clock time. Since
    we don't have enough samples, the flame chart will be approximate: Not all
    function calls in it are recorded. Still quite useful to see what is going
    on.
    """
    if not profiles:
        return []
    output = []
    stack_with_start_times = []
    start_time = profiles[0].timestamp
    last_time = profiles[-1].timestamp + 2
    prev_sample = 0

    for profile in profiles + [StackSample([], last_time, 1)]:
        if profile.timestamp == -1.0: # sampling failed
            continue
        curr_sample = profile.timestamp - start_time

        # estimate start time of functions in the middle between the previous
        # sample and the current one
        curr_time = (curr_sample + prev_sample) // 2

        # find index up to where two consecutive stack samples agree
        sampled_stack = profile.stack
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
        prev_sample = curr_sample
    output.sort(key=lambda x: (x[1], x[1] - x[2], x[0]))
    return output

def export_json(log, state, fn):
    """ Create a chrome-tracing-compatible json file """
    import json
    # 1. produce trace events for all the reconstructed stack functions
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
    s = state.profiles[0].timestamp
    for p in state.profiles:
        ts = (p.timestamp - s) * 0.001
        # 2. produce instant events for all samples to make it visible where
        # the process was blocked
        # XXX find a way to trace system calls somehow?
        # {"name": "OutOfMemory", "ph": "i", "ts": 1234523.3, "pid": 2343, "tid": 2347, "s": "g"}
        events.append(dict(ph="i", pid=1, tid="sample", ts=ts, name="sample"))

        # 3. Add a counter event to show memory usage, if we have it
        # {..., "name": "ctr", "ph": "C", "ts":  0, "args": {"cats":  0}},
        if state.profile_memory:
            events.append(dict(ph="C", pid=1, name="memory", ts=(p.timestamp - s) * 0.001, args=dict(memory=p.mem_in_kb)))
    with open(fn, "w") as f:
        json.dump(result, f)


def write_chrome_tracing_file(stats, filename):
    output = coalesce(stats.profiles, factor=0.001, skew=1)
    o = [(stats._get_name(a), start, stop) for (a, start, stop) in output]
    export_json(o, stats, filename)
