"""
操作系统适配器包
"""

import platform

# 基础适配器始终导入
from .base_adapter import BaseOSAdapter
from .factory import get_os_adapter

# 根据当前系统导入相应的适配器
current_os = platform.system()
if current_os == 'Windows':
    from .windows_adapter import WindowsAdapter
    __all__ = ['BaseOSAdapter', 'WindowsAdapter', 'get_os_adapter']
elif current_os == 'Darwin':  # macOS
    from .darwin_adapter import DarwinAdapter
    __all__ = ['BaseOSAdapter', 'DarwinAdapter', 'get_os_adapter']
else:
    __all__ = ['BaseOSAdapter', 'get_os_adapter']
