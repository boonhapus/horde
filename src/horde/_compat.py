import time as time_
import platform
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
