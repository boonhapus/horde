import platform
import sys

IS_PY_310_COMPATIBLE = sys.version_info >= (3, 10, 0)
IS_WINDOWS = platform.system() == "Windows"
