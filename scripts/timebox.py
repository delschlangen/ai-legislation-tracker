#!/usr/bin/env python3
"""
timebox.py

Runs calls with a time limit on the whole of each one. Standard library only.

A network timeout only limits a single wait on a socket. A server that keeps
sending one byte at a time never trips it, and could hold one check for hours:
long enough for the workflow's own time limit to end the run with no report at
all. So the link and upstream checks run through here, where every call has a
deadline for all of it, and the run as a whole has a budget.

A call that overruns is abandoned, not stopped, because Python cannot stop a
thread. Its thread is a daemon, so it does not keep the process alive, and
whatever it returns later is ignored.
"""

import queue
import threading
import time

DONE = "done"                # the call returned; the value is what it returned
FAILED = "failed"            # the call raised; the value is the exception
GAVE_UP = "gave up"          # still running at its deadline; the value is None
OUT_OF_TIME = "out of time"  # never started: the budget was spent; the value is None


def run_all(function, items, seconds, workers=1, pause=0.0, budget=None):
    """Call function(item) for every item, at most `workers` at a time.

    Returns {item: (state, value)} with one entry per item; the states are the
    constants above. Items must be distinct and hashable.

    seconds: how long one call may take, from the moment it starts.
    pause:   a wait before each call after the first, for APIs that ask
             callers not to hurry.
    budget:  how long all of it may take. Once it is spent no further call is
             started; the calls already running still get their `seconds`.
             So the whole thing returns within about budget + seconds.
    """
    finished = queue.Queue()

    def work(item):
        try:
            outcome = (DONE, function(item))
        except BaseException as exc:  # noqa: BLE001 - hand every failure to the caller
            outcome = (FAILED, exc)
        finished.put((item, outcome))

    began = time.monotonic()
    waiting = list(items)[::-1]
    running = {}
    results = {}
    started_one = False
    while waiting or running:
        while waiting and len(running) < workers:
            if budget is not None and time.monotonic() - began >= budget:
                results.update((item, (OUT_OF_TIME, None)) for item in waiting)
                waiting = []
                break
            if pause and started_one:
                time.sleep(pause)
            item = waiting.pop()
            running[item] = time.monotonic()
            started_one = True
            threading.Thread(target=work, args=(item,), daemon=True).start()
        if not running:
            continue

        # Wait for the next call to finish, but no longer than the nearest deadline.
        wait = min(running.values()) + seconds - time.monotonic()
        try:
            item, outcome = finished.get(timeout=max(0.0, wait))
        except queue.Empty:
            pass
        else:
            # An answer from a call already given up on is ignored, so the
            # outcome reported for it never changes after the fact.
            if item in running:
                del running[item]
                results[item] = outcome

        now = time.monotonic()
        for item in [i for i, started in running.items() if now - started >= seconds]:
            del running[item]
            results[item] = (GAVE_UP, None)
    return results
