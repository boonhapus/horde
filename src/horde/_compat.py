from typing import Callable
import functools as ft
import time as time_
import platform
import inspect
import sys

IS_PY_310_COMPATIBLE = sys.version_info >= (3, 10, 0)
IS_WINDOWS = platform.system() == "Windows"

# Why?
# - https://github.com/Textualize/textual/blob/f8aa18a953bbd02b3decd3ec2eece5670543e3b7/src/textual/_time.py#L12
# - https://github.com/python-trio/trio/issues/33
#
# It's recommended by people smarter than me, because OSes have inconsistencies.
if IS_WINDOWS:
    get_time = time_.perf_counter
else:
    get_time = time_.monotonic


if sys.version_info >= (3, 8, 0):
    iscoroutinefunction = inspect.iscoroutinefunction

# functools._unwrap_partial not release until 3.8
else:
    def iscoroutinefunction(fn: Callable) -> bool:
        while isinstance(fn, ft.partial):
            fn = fn.func

        return inspect.iscoroutinefunction(fn)

    iscoroutinefunction.__doc__ = inspect.iscoroutinefunction.__doc__
