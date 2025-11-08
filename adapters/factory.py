"""
操作系统适配器工厂模块
"""

import sys
import platform

# 先检查操作系统，只导入当前系统需要的适配器
current_os = platform.system()

# 定义基础适配器导入
from .base_adapter import BaseOSAdapter

# 根据当前系统导入相应的适配器
if current_os == 'Windows':
    from .windows_adapter import WindowsAdapter
elif current_os == 'Darwin':  # macOS
    from .darwin_adapter import DarwinAdapter

def get_os_adapter() -> BaseOSAdapter:
    """根据当前操作系统返回相应的适配器实例

    Returns:
        BaseOSAdapter: 对应操作系统的适配器实例
    """
    if current_os == 'Windows':
        return WindowsAdapter()
    elif current_os == 'Darwin':  # macOS
        return DarwinAdapter()
    else:
        print(f"不支持的操作系统: {current_os}")
        sys.exit(1)

# 获取全局适配器实例
os_adapter = get_os_adapter()