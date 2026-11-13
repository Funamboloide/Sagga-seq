# SPDX-License-Identifier: GPL-3.0-only
"""Trial and error: a target's settings nudged one at a time, kept when the sound gets closer to the original.

`params` lists the knobs: (path in the plan, step, low, high). A path is a tuple of keys ("scenes", "A", "amp_eg",
"decay"). Each round tries every knob up and down by its step; a better score keeps the move; when no knob helps,
the steps halve. It stops after `budget` seconds or when the steps are small. The score is `distance()` (dB)."""
import copy
import time

import numpy as np

from .render import distance


def _get(p, path):
    for k in path:
        p = p[k]
    return p


def _set(p, path, v):
    for k in path[:-1]:
        p = p[k]
    p[path[-1]] = v


def refine(plan, target, simulate, params, budget=60.0, min_step_frac=0.05, log=None):
    """(the best plan, its score, the score it started from)"""
    t_end = time.time() + budget
    best = copy.deepcopy(plan)
    params = [(path, step, lo, hi) for path, step, lo, hi in params if _exists(best, path)]
    score = distance(target, simulate(best))
    start = score
    steps = {path: step for path, step, lo, hi in params}
    restarts = 0
    while time.time() < t_end:
        improved = False
        for path, step0, lo, hi in params:
            if time.time() >= t_end:
                break
            step = steps[path]
            if step < step0 * min_step_frac:
                continue
            cur = float(_get(best, path))
            for v in (cur + step, cur - step):
                v = float(np.clip(v, lo, hi))
                if v == cur:
                    continue
                cand = copy.deepcopy(best)
                _set(cand, path, v)
                s = distance(target, simulate(cand))
                if s < score - 1e-3:
                    best, score, improved = cand, s, True
                    if log:
                        log("%s -> %.3f (%.2f dB)" % ("/".join(map(str, path)), v, s))
                    break
            else:
                steps[path] = step * 0.5
        if not improved and all(steps[p] < s0 * min_step_frac for p, s0, _, _ in params):
            if restarts >= 2 or time.time() > t_end - 1.0:
                break
            restarts += 1                               # (the big steps again from here: a way out of a corner)
            steps = {path: step for path, step, lo, hi in params}
    return best, score, start


def _exists(p, path):
    try:
        _get(p, path)
        return True
    except (KeyError, TypeError, IndexError):
        return False
