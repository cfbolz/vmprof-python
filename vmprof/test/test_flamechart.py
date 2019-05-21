import pytest
from vmprof.flamechart import coalesce, write_chrome_tracing_file
from vmprof.reader import StackSample

def test_coalesce():
    profiles = [StackSample([1, 2], 5, 1)]
    r = coalesce(profiles)
    assert r == [(1, 0, 1), (2, 0, 1)]

    profiles = [StackSample([1, 2], 1, 1),
                StackSample([1, 2], 2, 1)]
    r = coalesce(profiles)
    assert r == [(1, 0, 2), (2, 0, 2)]

    profiles = [StackSample([1, 2], 0, 1),
                StackSample([1, 3], 2, 1)]
    r = coalesce(profiles)
    assert r == [(1, 0, 3), (2, 0, 1), (3, 1, 3)]

    profiles = [StackSample([1], 0, 1),
                StackSample([1, 2], 2, 1),
                StackSample([1], 4, 1)]
    r = coalesce(profiles)
    assert r == [(1, 0, 5), (2, 1, 3)]

    profiles = [StackSample([1], 0, 1),
                StackSample([1, 2], 2, 1),
                StackSample([3], 4, 1)]
    r = coalesce(profiles)
    assert r == [(1, 0, 3), (2, 1, 3), (3, 3, 5)]

    profiles = [StackSample([1], 0, 1),
                StackSample([1, 2], 2, 1),
                StackSample([3, 2], 4, 1)]
    r = coalesce(profiles)
    assert r == [(1, 0, 3), (2, 1, 3), (2, 3, 5), (3, 3, 5)]

def test_coalesce_start_at_middle():
    profiles = [StackSample([1, 2], 0, 1), StackSample([1, 3], 2, 1), StackSample([1, 3], 5, 1)]
    r = coalesce(profiles)
    assert r == [(1, 0, 6), (2, 0, 1), (3, 1, 6)]


def test_larger_steps():
    profiles = [StackSample([1], 0, 1),
                StackSample([1, 2], 6, 1),
                StackSample([3], 12, 1)]
    r = coalesce(profiles)
    assert r == [(1, 0, 9), (2, 3, 9), (3, 9, 13)]

def test_even_more():
    profiles = [StackSample([1, 2], 0, 1),
                StackSample([1, 2], 10, 1)]
    r = coalesce(profiles)
    assert r == [(1, 0, 11), (2, 0, 11)]

    profiles = [StackSample([1], 0, 1),
                StackSample([1, 2, 3, 4, 5], 10, 1),
                StackSample([1, 2, 6], 16, 1),
                StackSample([1, 7, 8], 22, 1)]
    r = coalesce(profiles)
    assert r == [(1, 0, 23), (2, 5, 19), (3, 5, 13), (4, 5, 13), (5, 5, 13),
                 (6, 13, 19), (7, 19, 23), (8, 19, 23)]

def test_skew():
    profiles = [StackSample([1], 0, 1),
                StackSample([1, 2, 3, 4], 100, 1),
                StackSample([1, 2], 300, 1)]
    r = coalesce(profiles, skew=1)
    assert r == [(1, 0, 301), (2, 50, 300), (3, 51, 200), (4, 52, 199)]

def test_smoke():
    import py
    import vmprof
    import tempfile
    import json
    path = py.path.local(__file__).join('..', 'python2-version-timers')
    stats = vmprof.read_profile(str(path))
    jsonfile = tempfile.NamedTemporaryFile(delete=False)
    write_chrome_tracing_file(stats, jsonfile.name)
    d = json.load(jsonfile.name) # check that it's valid json
