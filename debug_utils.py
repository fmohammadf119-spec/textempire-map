#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ابزارهای دیباگ برای ربات
"""

import traceback
from datetime import datetime

def debug_print(function_name, step, message="", data=None):
    """پرینت دیباگ استاندارد"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[DEBUG][{timestamp}][{function_name}][{step}] {message}")
    if data is not None:
        print(f"[DEBUG][{timestamp}][{function_name}][{step}] Data: {data}")

def debug_error(function_name, step, error, data=None):
    """پرینت خطای دیباگ"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[ERROR][{timestamp}][{function_name}][{step}] {error}")
    if data is not None:
        print(f"[ERROR][{timestamp}][{function_name}][{step}] Data: {data}")
    print(f"[ERROR][{timestamp}][{function_name}][{step}] Traceback: {traceback.format_exc()}")

def debug_success(function_name, step, message="", data=None):
    """پرینت موفقیت دیباگ"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[SUCCESS][{timestamp}][{function_name}][{step}] {message}")
    if data is not None:
        print(f"[SUCCESS][{timestamp}][{function_name}][{step}] Data: {data}")

def debug_warning(function_name, step, message="", data=None):
    """پرینت هشدار دیباگ"""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[WARNING][{timestamp}][{function_name}][{step}] {message}")
    if data is not None:
        print(f"[WARNING][{timestamp}][{function_name}][{step}] Data: {data}")

def debug_function_entry(function_name, **kwargs):
    """پرینت ورود به تابع"""
    debug_print(function_name, "ENTRY", f"Function started", kwargs)

def debug_function_exit(function_name, result=None):
    """پرینت خروج از تابع"""
    debug_print(function_name, "EXIT", f"Function completed", result)

def debug_function_error(function_name, error):
    """پرینت خطای تابع"""
    debug_error(function_name, "ERROR", str(error))
