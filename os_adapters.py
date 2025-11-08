"""
操作系统适配器入口模块
"""

from adapters.factory import os_adapter
from adapters.base_adapter import BaseOSAdapter
from adapters.windows_adapter import WindowsAdapter
from adapters.darwin_adapter import DarwinAdapter
from adapters.factory import get_os_adapter

__all__ = ['os_adapter', 'BaseOSAdapter', 'WindowsAdapter', 'DarwinAdapter', 'get_os_adapter']
