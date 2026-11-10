# -*- coding: utf-8 -*-
"""
Universal XMouse Ghost Engine CLI & MCP Runner (`/xmouse` Skill Script).
Self-contained 4-Pillar OS primitive runner (Ghost Click Engine, Multi-Cursor HUD,
Hybrid UIA < 5ms + Set-of-Mark Vision Grid, and < 10ms Reflex Yield).
"""

import argparse
import ctypes
import json
import math
import os
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

sys.dont_write_bytecode = True

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

try:
    from PIL import Image, ImageDraw

    HAS_PIL = True
except ImportError:
    HAS_PIL = False

__version__ = "1.0.0"

# Win32 Constants
WM_DESTROY = 0x0002
WM_SETTEXT = 0x000C
WM_GETTEXT = 0x000D
WM_GETTEXTLENGTH = 0x000E
WM_PAINT = 0x000F
WM_CLOSE = 0x0010
WM_QUIT = 0x0012
WM_CHAR = 0x0102
WM_COMMAND = 0x0111
WM_SYSCOMMAND = 0x0112
SC_MINIMIZE = 0xF020
SC_MAXIMIZE = 0xF030
SC_RESTORE = 0xF012
WM_MOUSEMOVE = 0x0200
WM_LBUTTONDOWN = 0x0201
WM_LBUTTONUP = 0x0202
WM_LBUTTONDBLCLK = 0x0203
WM_RBUTTONDOWN = 0x0204
WM_RBUTTONUP = 0x0205
WM_RBUTTONDBLCLK = 0x0206
WM_MBUTTONDOWN = 0x0207
WM_MBUTTONUP = 0x0208
WM_MBUTTONDBLCLK = 0x0209
WM_MOUSEWHEEL = 0x020A
WM_MOUSEHWHEEL = 0x020E
BM_CLICK = 0x00F5
EM_SETSEL = 0x00B1

MK_LBUTTON = 0x0001
MK_RBUTTON = 0x0002
MK_MBUTTON = 0x0010
SMTO_ABORTIFHUNG = 0x0002
CWP_SKIPINVISIBLE = 0x0001
CWP_SKIPDISABLED = 0x0002

GWL_STYLE = -16
BS_TYPEMASK = 0x0000000F
BS_CHECKBOX = 0x00000002
BS_AUTOCHECKBOX = 0x00000003
BS_RADIOBUTTON = 0x00000004
BS_3STATE = 0x00000005
BS_AUTO3STATE = 0x00000006
BS_GROUPBOX = 0x00000007
BS_AUTORADIOBUTTON = 0x00000009

UIA_INVOKE_PATTERN_ID = 10000
UIA_VALUE_PATTERN_ID = 10002
UIA_TOGGLE_PATTERN_ID = 10015

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79
MONITORINFOF_PRIMARY = 0x00000001
MDT_EFFECTIVE_DPI = 0

PW_CLIENTONLY = 0x00000001
PW_RENDERFULLCONTENT = 0x00000002
SRCCOPY = 0x00CC0020
BI_RGB = 0
DIB_RGB_COLORS = 0

WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
WS_EX_TOPMOST = 0x00000008
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
HUD_EX_STYLE = (
    WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOPMOST | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
)
LWA_COLORKEY = 0x00000001
COLORKEY_RGB = 0x00FF00FF

AGENT_PALETTE: Dict[str, str] = {
    "Agent-1": "#2563EB",
    "Agent-2": "#10B981",
    "Agent-3": "#F59E0B",
    "Agent-4": "#EC4899",
    "Agent-5": "#8B5CF6",
    "Agent-6": "#06B6D4",
}
DEFAULT_COLOR_LIST = list(AGENT_PALETTE.values())

if sys.platform == "win32":
    import ctypes.wintypes as wt

    user32 = ctypes.windll.user32
    gdi32 = ctypes.windll.gdi32
    kernel32 = ctypes.windll.kernel32
    ole32 = ctypes.windll.ole32
    try:
        shcore = ctypes.windll.shcore
    except OSError:
        shcore = None
    ole32.CoInitialize.argtypes = [ctypes.c_void_p]
    ole32.CoInitialize.restype = ctypes.c_long
    ole32.CoUninitialize.argtypes = []
    ole32.CoUninitialize.restype = None
    WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    MONITORENUMPROC = ctypes.WINFUNCTYPE(
        wt.BOOL, wt.HMONITOR, wt.HDC, ctypes.POINTER(wt.RECT), wt.LPARAM
    )

    class MONITORINFOEXW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wt.DWORD),
            ("rcMonitor", wt.RECT),
            ("rcWork", wt.RECT),
            ("dwFlags", wt.DWORD),
            ("szDevice", wt.WCHAR * 32),
        ]

    user32.GetSystemMetrics.argtypes = [ctypes.c_int]
    user32.GetSystemMetrics.restype = ctypes.c_int
    user32.EnumDisplayMonitors.argtypes = [
        wt.HDC,
        ctypes.POINTER(wt.RECT),
        MONITORENUMPROC,
        wt.LPARAM,
    ]
    user32.EnumDisplayMonitors.restype = wt.BOOL
    user32.GetMonitorInfoW.argtypes = [wt.HMONITOR, ctypes.c_void_p]
    user32.GetMonitorInfoW.restype = wt.BOOL

    class BITMAPINFOHEADER(ctypes.Structure):
        _fields_ = [
            ("biSize", wt.DWORD),
            ("biWidth", wt.LONG),
            ("biHeight", wt.LONG),
            ("biPlanes", wt.WORD),
            ("biBitCount", wt.WORD),
            ("biCompression", wt.DWORD),
            ("biSizeImage", wt.DWORD),
            ("biXPelsPerMeter", wt.LONG),
            ("biYPelsPerMeter", wt.LONG),
            ("biClrUsed", wt.DWORD),
            ("biClrImportant", wt.DWORD),
        ]

    class BITMAPINFO(ctypes.Structure):
        _fields_ = [
            ("bmiHeader", BITMAPINFOHEADER),
            ("bmiColors", wt.DWORD * 3),
        ]

    user32.IsWindow.argtypes = [wt.HWND]
    user32.IsWindow.restype = wt.BOOL
    user32.IsWindowVisible.argtypes = [wt.HWND]
    user32.IsWindowVisible.restype = wt.BOOL
    user32.IsWindowEnabled.argtypes = [wt.HWND]
    user32.IsWindowEnabled.restype = wt.BOOL
    user32.EnumWindows.argtypes = [WNDENUMPROC, wt.LPARAM]
    user32.EnumWindows.restype = wt.BOOL
    user32.EnumChildWindows.argtypes = [wt.HWND, WNDENUMPROC, wt.LPARAM]
    user32.EnumChildWindows.restype = wt.BOOL
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wt.POINT)]
    user32.GetCursorPos.restype = wt.BOOL
    user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
    user32.SetCursorPos.restype = wt.BOOL
    user32.GetWindowRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
    user32.GetWindowRect.restype = wt.BOOL
    user32.GetClientRect.argtypes = [wt.HWND, ctypes.POINTER(wt.RECT)]
    user32.GetClientRect.restype = wt.BOOL
    user32.ScreenToClient.argtypes = [wt.HWND, ctypes.POINTER(wt.POINT)]
    user32.ScreenToClient.restype = wt.BOOL
    user32.ClientToScreen.argtypes = [wt.HWND, ctypes.POINTER(wt.POINT)]
    user32.ClientToScreen.restype = wt.BOOL
    user32.ChildWindowFromPointEx.argtypes = [wt.HWND, wt.POINT, wt.UINT]
    user32.ChildWindowFromPointEx.restype = wt.HWND
    user32.GetWindowTextLengthW.argtypes = [wt.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetClassNameW.argtypes = [wt.HWND, wt.LPWSTR, ctypes.c_int]
    user32.GetClassNameW.restype = ctypes.c_int
    user32.GetDlgCtrlID.argtypes = [wt.HWND]
    user32.GetDlgCtrlID.restype = ctypes.c_int
    user32.GetWindowLongW.argtypes = [wt.HWND, ctypes.c_int]
    user32.GetWindowLongW.restype = ctypes.c_long
    user32.GetWindowThreadProcessId.argtypes = [wt.HWND, ctypes.POINTER(wt.DWORD)]
    user32.GetWindowThreadProcessId.restype = wt.DWORD
    user32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
    user32.PostMessageW.restype = wt.BOOL
    user32.SendMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
    user32.SendMessageW.restype = ctypes.c_ssize_t
    user32.SendMessageTimeoutW.argtypes = [
        wt.HWND,
        wt.UINT,
        wt.WPARAM,
        wt.LPARAM,
        wt.UINT,
        wt.UINT,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    user32.SendMessageTimeoutW.restype = ctypes.c_ssize_t
    user32.GetWindowDC.argtypes = [wt.HWND]
    user32.GetWindowDC.restype = wt.HDC
    user32.GetDC.argtypes = [wt.HWND]
    user32.GetDC.restype = wt.HDC
    user32.ReleaseDC.argtypes = [wt.HWND, wt.HDC]
    user32.ReleaseDC.restype = ctypes.c_int
    user32.PrintWindow.argtypes = [wt.HWND, wt.HDC, wt.UINT]
    user32.PrintWindow.restype = wt.BOOL
    gdi32.CreateCompatibleDC.argtypes = [wt.HDC]
    gdi32.CreateCompatibleDC.restype = wt.HDC
    gdi32.CreateCompatibleBitmap.argtypes = [wt.HDC, ctypes.c_int, ctypes.c_int]
    gdi32.CreateCompatibleBitmap.restype = wt.HBITMAP
    gdi32.SelectObject.argtypes = [wt.HDC, wt.HGDIOBJ]
    gdi32.SelectObject.restype = wt.HGDIOBJ
    gdi32.BitBlt.argtypes = [
        wt.HDC,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wt.HDC,
        ctypes.c_int,
        ctypes.c_int,
        wt.DWORD,
    ]
    gdi32.BitBlt.restype = wt.BOOL
    gdi32.GetDIBits.argtypes = [
        wt.HDC,
        wt.HBITMAP,
        wt.UINT,
        wt.UINT,
        ctypes.c_void_p,
        ctypes.POINTER(BITMAPINFO),
        wt.UINT,
    ]
    gdi32.GetDIBits.restype = ctypes.c_int
    gdi32.DeleteObject.argtypes = [wt.HGDIOBJ]
    gdi32.DeleteObject.restype = wt.BOOL
    gdi32.DeleteDC.argtypes = [wt.HDC]
    gdi32.DeleteDC.restype = wt.BOOL

    try:
        uia_core = ctypes.windll.UIAutomationCore
        uia_core.UiaNodeFromHandle.argtypes = [wt.HWND, ctypes.POINTER(ctypes.c_void_p)]
        uia_core.UiaNodeFromHandle.restype = ctypes.c_long
        uia_core.UiaGetPatternProvider.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_void_p),
        ]
        uia_core.UiaGetPatternProvider.restype = ctypes.c_long
        uia_core.InvokePattern_Invoke.argtypes = [ctypes.c_void_p]
        uia_core.InvokePattern_Invoke.restype = ctypes.c_long
        uia_core.ValuePattern_SetValue.argtypes = [ctypes.c_void_p, wt.LPCWSTR]
        uia_core.ValuePattern_SetValue.restype = ctypes.c_long
        uia_core.TogglePattern_Toggle.argtypes = [ctypes.c_void_p]
        uia_core.TogglePattern_Toggle.restype = ctypes.c_long
        uia_core.UiaPatternRelease.argtypes = [ctypes.c_void_p]
        uia_core.UiaPatternRelease.restype = wt.BOOL
        uia_core.UiaNodeRelease.argtypes = [ctypes.c_void_p]
        uia_core.UiaNodeRelease.restype = wt.BOOL
    except OSError:
        uia_core = None


def enable_per_monitor_dpi_awareness() -> Dict[str, Any]:
    if sys.platform != "win32":
        return {"ok": True, "mode": "non_win32_native"}
    try:
        user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_ssize_t]
        user32.SetProcessDpiAwarenessContext.restype = wt.BOOL
        if user32.SetProcessDpiAwarenessContext(ctypes.c_ssize_t(-4)):
            return {"ok": True, "mode": "PER_MONITOR_AWARE_V2"}
    except (AttributeError, OSError):
        pass
    if shcore is not None:
        try:
            hr = shcore.SetProcessDpiAwareness(2)
            if hr in (0, -2147024891):
                return {"ok": True, "mode": "PER_MONITOR_AWARE_V1_OR_LOCKED"}
        except (AttributeError, OSError):
            pass
    try:
        user32.SetProcessDPIAware()
        return {"ok": True, "mode": "SYSTEM_DPI_AWARE"}
    except (AttributeError, OSError) as exc:
        return {"ok": False, "mode": "UNAWARE", "error": str(exc)}


_DPI_INIT_STATUS = enable_per_monitor_dpi_awareness()


def get_virtual_screen_bounds() -> Tuple[int, int, int, int]:
    if sys.platform == "win32":
        vx = int(user32.GetSystemMetrics(SM_XVIRTUALSCREEN))
        vy = int(user32.GetSystemMetrics(SM_YVIRTUALSCREEN))
        vw = int(user32.GetSystemMetrics(SM_CXVIRTUALSCREEN))
        vh = int(user32.GetSystemMetrics(SM_CYVIRTUALSCREEN))
        if vw > 0 and vh > 0:
            return (vx, vy, vw, vh)
    return (0, 0, 1920, 1080)


def list_monitors() -> Dict[str, Any]:
    t0 = time.perf_counter()
    vx, vy, vw, vh = get_virtual_screen_bounds()
    vscreen = {
        "left": vx,
        "top": vy,
        "right": vx + vw,
        "bottom": vy + vh,
        "width": vw,
        "height": vh,
    }
    if sys.platform != "win32":
        return {
            "ok": True,
            "monitors": [
                {
                    "index": 1,
                    "hmonitor": 1,
                    "device": "DISPLAY1",
                    "is_primary": True,
                    "rect": vscreen,
                    "work_rect": vscreen,
                    "dpi_x": 96,
                    "dpi_y": 96,
                    "scale_percent": 100,
                }
            ],
            "count": 1,
            "virtual_screen": vscreen,
            "dpi_awareness": _DPI_INIT_STATUS,
            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    monitors: List[Dict[str, Any]] = []

    def _mon_cb(hmon: int, _hdc: int, _lprc: Any, _lparam: int) -> bool:
        info = MONITORINFOEXW()
        info.cbSize = ctypes.sizeof(MONITORINFOEXW)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(info)):
            dpi_x = ctypes.c_uint(96)
            dpi_y = ctypes.c_uint(96)
            if shcore is not None:
                try:
                    shcore.GetDpiForMonitor(
                        wt.HMONITOR(hmon),
                        MDT_EFFECTIVE_DPI,
                        ctypes.byref(dpi_x),
                        ctypes.byref(dpi_y),
                    )
                except (AttributeError, OSError):
                    pass
            ml, mt, mr, mb = (
                int(info.rcMonitor.left),
                int(info.rcMonitor.top),
                int(info.rcMonitor.right),
                int(info.rcMonitor.bottom),
            )
            wl, wt_y, wr, wb = (
                int(info.rcWork.left),
                int(info.rcWork.top),
                int(info.rcWork.right),
                int(info.rcWork.bottom),
            )
            dx = int(dpi_x.value) or 96
            dy = int(dpi_y.value) or 96
            monitors.append(
                {
                    "index": len(monitors) + 1,
                    "hmonitor": int(hmon),
                    "device": info.szDevice,
                    "is_primary": bool(info.dwFlags & MONITORINFOF_PRIMARY),
                    "rect": {
                        "left": ml,
                        "top": mt,
                        "right": mr,
                        "bottom": mb,
                        "width": mr - ml,
                        "height": mb - mt,
                    },
                    "work_rect": {
                        "left": wl,
                        "top": wt_y,
                        "right": wr,
                        "bottom": wb,
                        "width": wr - wl,
                        "height": wb - wt_y,
                    },
                    "dpi_x": dx,
                    "dpi_y": dy,
                    "scale_percent": int(round((dx / 96.0) * 100.0)),
                }
            )
        return True

    c_mon_cb = MONITORENUMPROC(_mon_cb)
    user32.EnumDisplayMonitors(0, None, c_mon_cb, 0)
    return {
        "ok": True,
        "monitors": monitors,
        "count": len(monitors),
        "virtual_screen": vscreen,
        "dpi_awareness": _DPI_INIT_STATUS,
        "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def pack_lparam(x: int, y: int) -> int:
    cx = max(-32768, min(32767, int(x)))
    cy = max(-32768, min(32767, int(y)))
    return ((cy & 0xFFFF) << 16) | (cx & 0xFFFF)


def unpack_lparam(lparam: int) -> Tuple[int, int]:
    raw_x = int(lparam) & 0xFFFF
    raw_y = (int(lparam) >> 16) & 0xFFFF
    return ((raw_x ^ 0x8000) - 0x8000, (raw_y ^ 0x8000) - 0x8000)


def get_physical_cursor_pos() -> Tuple[int, int]:
    if sys.platform == "win32":
        pt = wt.POINT()
        if user32.GetCursorPos(ctypes.byref(pt)):
            return (int(pt.x), int(pt.y))
    return (0, 0)


def _send_msg(hwnd: int, msg: int, wparam: int, lparam: int, async_post: bool = False) -> bool:
    if sys.platform != "win32":
        return False
    if async_post:
        return bool(user32.PostMessageW(hwnd, msg, wparam, lparam))
    res_out = ctypes.c_size_t(0)
    ok = user32.SendMessageTimeoutW(
        hwnd, msg, wparam, lparam, SMTO_ABORTIFHUNG, 500, ctypes.byref(res_out)
    )
    return bool(ok)


def _get_class_name(hwnd: int) -> str:
    if sys.platform != "win32":
        return ""
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def _read_window_text(hwnd: int, class_name: str = "") -> str:
    if sys.platform != "win32":
        return ""
    length = user32.GetWindowTextLengthW(hwnd)
    if length > 0:
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        if buf.value:
            return buf.value
    low_cls = class_name.lower()
    if "edit" in low_cls or "combobox" in low_cls:
        pid = wt.DWORD(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if int(pid.value) != os.getpid():
            res_len = ctypes.c_size_t(0)
            ok = user32.SendMessageTimeoutW(
                hwnd, WM_GETTEXTLENGTH, 0, 0, SMTO_ABORTIFHUNG, 20, ctypes.byref(res_len)
            )
            if ok and 0 < res_len.value <= 4096:
                buf2 = ctypes.create_unicode_buffer(int(res_len.value) + 1)
                user32.SendMessageTimeoutW(
                    hwnd,
                    WM_GETTEXT,
                    int(res_len.value) + 1,
                    ctypes.addressof(buf2),
                    SMTO_ABORTIFHUNG,
                    20,
                    ctypes.byref(res_len),
                )
                return buf2.value
    return ""


def _classify_control_type(hwnd: int, class_name: str) -> str:
    low = class_name.lower()
    if "button" in low:
        if sys.platform == "win32":
            style = user32.GetWindowLongW(hwnd, GWL_STYLE) & BS_TYPEMASK
            if style in {BS_CHECKBOX, BS_AUTOCHECKBOX, BS_3STATE, BS_AUTO3STATE}:
                return "CheckBox"
            if style in {BS_RADIOBUTTON, BS_AUTORADIOBUTTON}:
                return "RadioButton"
            if style == BS_GROUPBOX:
                return "GroupBox"
        return "Button"
    if "edit" in low or "richedit" in low or "textbox" in low:
        return "Edit"
    if "combobox" in low:
        return "ComboBox"
    if "listbox" in low or "syslistview" in low:
        return "List"
    if "systreeview" in low:
        return "Tree"
    if "toolbar" in low:
        return "ToolBar"
    if "trackbar" in low or "slider" in low:
        return "Slider"
    if "scrollbar" in low:
        return "ScrollBar"
    if "static" in low or "label" in low:
        return "Text"
    if "canvas" in low or "gl" in low or "viewport" in low:
        return "Canvas"
    return "Pane"


def _infer_patterns(hwnd: int, control_type: str, include_uia_patterns: bool) -> List[str]:
    patterns: List[str] = []
    if control_type in {"Button", "RadioButton", "ToolBar"}:
        patterns.append("InvokePattern")
    elif control_type == "CheckBox":
        patterns.extend(["TogglePattern", "InvokePattern"])
    elif control_type in {"Edit", "ComboBox", "Slider"}:
        patterns.append("ValuePattern")
    elif control_type in {"List", "Tree", "Tab"}:
        patterns.append("SelectionPattern")

    if include_uia_patterns and not patterns and sys.platform == "win32" and uia_core is not None:
        hnode = ctypes.c_void_p()
        if uia_core.UiaNodeFromHandle(hwnd, ctypes.byref(hnode)) == 0 and hnode.value:
            try:
                for pat_id, pat_name in (
                    (UIA_INVOKE_PATTERN_ID, "InvokePattern"),
                    (UIA_VALUE_PATTERN_ID, "ValuePattern"),
                    (UIA_TOGGLE_PATTERN_ID, "TogglePattern"),
                ):
                    hpat = ctypes.c_void_p()
                    if (
                        uia_core.UiaGetPatternProvider(hnode, pat_id, ctypes.byref(hpat)) == 0
                        and hpat.value
                    ):
                        patterns.append(pat_name)
                        uia_core.UiaPatternRelease(hpat)
            finally:
                uia_core.UiaNodeRelease(hnode)
    return patterns


def _try_uia_invoke(hwnd: int) -> Optional[str]:
    if sys.platform != "win32" or uia_core is None:
        return None
    hr_co = ole32.CoInitialize(None)
    try:
        hnode = ctypes.c_void_p()
        if uia_core.UiaNodeFromHandle(hwnd, ctypes.byref(hnode)) != 0 or not hnode.value:
            return None
        try:
            style_type = int(user32.GetWindowLongW(hwnd, -16)) & 0x0F
            prefer_toggle = style_type in (2, 3, 5, 6)
            pattern_order = (
                [(UIA_TOGGLE_PATTERN_ID, "UIA_TogglePattern"), (UIA_INVOKE_PATTERN_ID, "UIA_InvokePattern")]
                if prefer_toggle
                else [(UIA_INVOKE_PATTERN_ID, "UIA_InvokePattern"), (UIA_TOGGLE_PATTERN_ID, "UIA_TogglePattern")]
            )
            for pat_id, pat_label in pattern_order:
                hpat = ctypes.c_void_p()
                if uia_core.UiaGetPatternProvider(hnode, pat_id, ctypes.byref(hpat)) == 0 and hpat.value:
                    try:
                        call_hr = (
                            uia_core.TogglePattern_Toggle(hpat)
                            if pat_id == UIA_TOGGLE_PATTERN_ID
                            else uia_core.InvokePattern_Invoke(hpat)
                        )
                        if call_hr == 0:
                            res_out = ctypes.c_size_t(0)
                            user32.SendMessageTimeoutW(
                                hwnd, 0x0000, 0, 0, SMTO_ABORTIFHUNG, 100, ctypes.byref(res_out)
                            )
                            return pat_label
                    finally:
                        uia_core.UiaPatternRelease(hpat)
        finally:
            uia_core.UiaNodeRelease(hnode)
    finally:
        if hr_co in (0, 1):
            ole32.CoUninitialize()
    return None


def _try_uia_set_value(hwnd: int, text: str) -> bool:
    if sys.platform != "win32" or uia_core is None:
        return False
    hr_co = ole32.CoInitialize(None)
    try:
        hnode = ctypes.c_void_p()
        if uia_core.UiaNodeFromHandle(hwnd, ctypes.byref(hnode)) != 0 or not hnode.value:
            return False
        try:
            hpat = ctypes.c_void_p()
            if uia_core.UiaGetPatternProvider(hnode, UIA_VALUE_PATTERN_ID, ctypes.byref(hpat)) == 0 and hpat.value:
                try:
                    return uia_core.ValuePattern_SetValue(hpat, text) == 0
                finally:
                    uia_core.UiaPatternRelease(hpat)
        finally:
            uia_core.UiaNodeRelease(hnode)
    finally:
        if hr_co in (0, 1):
            ole32.CoUninitialize()
    return False


def list_windows(visible_only: bool = True, title_filter: str = "") -> Dict[str, Any]:
    t0 = time.perf_counter()
    if sys.platform != "win32":
        return {
            "ok": True,
            "windows": [],
            "count": 0,
            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    raw_candidates: List[Dict[str, Any]] = []
    filt_low = title_filter.lower().strip()

    def _enum_cb(hwnd: int, _lparam: int) -> bool:
        vis = bool(user32.IsWindowVisible(hwnd))
        cls_name = _get_class_name(hwnd)
        title = _read_window_text(hwnd, cls_name)
        rc = wt.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rc))
        pid = wt.DWORD(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        w = int(rc.right - rc.left)
        h = int(rc.bottom - rc.top)
        raw_candidates.append(
            {
                "hwnd": int(hwnd),
                "title": title,
                "class_name": cls_name,
                "pid": int(pid.value),
                "visible": vis,
                "enabled": bool(user32.IsWindowEnabled(hwnd)),
                "rect": {
                    "left": int(rc.left),
                    "top": int(rc.top),
                    "right": int(rc.right),
                    "bottom": int(rc.bottom),
                    "width": w,
                    "height": h,
                },
                "center_xy": [int(rc.left) + w // 2, int(rc.top) + h // 2],
            }
        )
        return True

    c_cb = WNDENUMPROC(_enum_cb)
    user32.EnumWindows(c_cb, 0)

    exact = [
        w
        for w in raw_candidates
        if (not visible_only or w["visible"])
        and (not filt_low or filt_low in w["title"].lower() or filt_low in w["class_name"].lower())
    ]
    return {
        "ok": True,
        "windows": exact,
        "count": len(exact),
        "candidates_scanned": len(raw_candidates),
        "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def inspect_window(
    hwnd: int,
    visible_only: bool = True,
    include_uia_patterns: bool = False,
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    if sys.platform != "win32":
        return {
            "ok": False,
            "status": "UNSUPPORTED_PLATFORM",
            "hwnd": int(hwnd),
            "controls": [],
            "count": 0,
            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    if not hwnd or not user32.IsWindow(hwnd):
        return {
            "ok": False,
            "status": "INVALID_HWND",
            "error": f"Window handle {hwnd} is not a valid live HWND.",
            "hwnd": int(hwnd),
            "controls": [],
            "count": 0,
            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    win_rc = wt.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(win_rc))
    client_rc = wt.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(client_rc))
    win_cls = _get_class_name(hwnd)
    win_title = _read_window_text(hwnd, win_cls)

    children: List[Dict[str, Any]] = []

    def _child_cb(child_hwnd: int, _lparam: int) -> bool:
        vis = bool(user32.IsWindowVisible(child_hwnd))
        if visible_only and not vis:
            return True
        cls_name = _get_class_name(child_hwnd)
        name = _read_window_text(child_hwnd, cls_name)
        ctrl_id = int(user32.GetDlgCtrlID(child_hwnd))

        rc = wt.RECT()
        user32.GetWindowRect(child_hwnd, ctypes.byref(rc))
        w = max(0, int(rc.right - rc.left))
        h = max(0, int(rc.bottom - rc.top))

        pt_tl = wt.POINT(int(rc.left), int(rc.top))
        user32.ScreenToClient(hwnd, ctypes.byref(pt_tl))
        cl, ct = int(pt_tl.x), int(pt_tl.y)
        ctype = _classify_control_type(child_hwnd, cls_name)
        patterns = _infer_patterns(child_hwnd, ctype, include_uia_patterns)

        children.append(
            {
                "id": len(children) + 1,
                "hwnd": int(child_hwnd),
                "ctrl_id": ctrl_id,
                "name": name,
                "control_type": ctype,
                "class_name": cls_name,
                "visible": vis,
                "enabled": bool(user32.IsWindowEnabled(child_hwnd)),
                "rect": {
                    "left": int(rc.left),
                    "top": int(rc.top),
                    "right": int(rc.right),
                    "bottom": int(rc.bottom),
                    "width": w,
                    "height": h,
                },
                "client_rect": {
                    "left": cl,
                    "top": ct,
                    "right": cl + w,
                    "bottom": ct + h,
                    "width": w,
                    "height": h,
                },
                "center_xy": [int(rc.left) + w // 2, int(rc.top) + h // 2],
                "client_center_xy": [cl + w // 2, ct + h // 2],
                "supported_patterns": patterns,
            }
        )
        return True

    c_child_cb = WNDENUMPROC(_child_cb)
    hr_co = ole32.CoInitialize(None) if include_uia_patterns else -1
    try:
        user32.EnumChildWindows(hwnd, c_child_cb, 0)
    finally:
        if include_uia_patterns and hr_co in (0, 1):
            ole32.CoUninitialize()

    return {
        "ok": True,
        "status": "OK",
        "hwnd": int(hwnd),
        "title": win_title,
        "class_name": win_cls,
        "rect": {
            "left": int(win_rc.left),
            "top": int(win_rc.top),
            "right": int(win_rc.right),
            "bottom": int(win_rc.bottom),
            "width": int(win_rc.right - win_rc.left),
            "height": int(win_rc.bottom - win_rc.top),
        },
        "client_size": {
            "width": int(client_rc.right - client_rc.left),
            "height": int(client_rc.bottom - client_rc.top),
        },
        "controls": children,
        "count": len(children),
        "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def find_controls(
    hwnd: int,
    query: str = "",
    control_type: str = "",
    visible_only: bool = True,
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    tree = inspect_window(hwnd, visible_only=visible_only)
    if not tree.get("ok"):
        return tree
    q_low = query.lower().strip()
    ct_low = control_type.lower().strip()
    matched = [
        c
        for c in tree["controls"]
        if (not q_low or q_low in c["name"].lower() or q_low in c["class_name"].lower())
        and (not ct_low or c["control_type"].lower() == ct_low)
    ]
    return {
        "ok": True,
        "status": "OK",
        "hwnd": int(hwnd),
        "query": query,
        "control_type": control_type,
        "controls": matched,
        "count": len(matched),
        "candidates_scanned": tree["count"],
        "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def _resolve_child_at_client_point(hwnd: int, cx: int, cy: int) -> Tuple[int, int, int]:
    if sys.platform != "win32":
        return (hwnd, cx, cy)
    curr = hwnd
    curr_x, curr_y = cx, cy
    flags = CWP_SKIPINVISIBLE | CWP_SKIPDISABLED
    for _ in range(8):
        pt = wt.POINT(curr_x, curr_y)
        child = user32.ChildWindowFromPointEx(curr, pt, flags)
        if not child or child == curr:
            break
        screen_pt = wt.POINT(curr_x, curr_y)
        user32.ClientToScreen(curr, ctypes.byref(screen_pt))
        user32.ScreenToClient(child, ctypes.byref(screen_pt))
        curr = child
        curr_x, curr_y = int(screen_pt.x), int(screen_pt.y)
    return (curr, curr_x, curr_y)


def ghost_click(
    hwnd: int,
    x: Optional[int] = None,
    y: Optional[int] = None,
    button: str = "left",
    double: bool = False,
    use_uia: bool = True,
    coord_space: str = "client",
    bounds_check: bool = True,
    async_post: bool = False,
    resolve_child: bool = True,
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    pt_before = get_physical_cursor_pos()
    btn_norm = button.lower().strip()
    if btn_norm not in {"left", "right", "middle"}:
        return {
            "ok": False,
            "status": "INVALID_BUTTON",
            "hwnd": int(hwnd),
            "physical_cursor_delta_px": [0, 0],
            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    if sys.platform != "win32":
        return _posix_ghost_click_fallback(hwnd, x, y, btn_norm, double, t0)

    if not hwnd or not user32.IsWindow(hwnd):
        return {
            "ok": False,
            "status": "INVALID_HWND",
            "hwnd": int(hwnd),
            "physical_cursor_delta_px": [0, 0],
            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    client_rc = wt.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(client_rc))
    width = max(0, int(client_rc.right - client_rc.left))
    height = max(0, int(client_rc.bottom - client_rc.top))

    explicit_xy = (x is not None) or (y is not None)
    if not explicit_xy:
        cx = width // 2 if width > 0 else 0
        cy = height // 2 if height > 0 else 0
    else:
        raw_x = int(x) if x is not None else (width // 2 if width > 0 else 0)
        raw_y = int(y) if y is not None else (height // 2 if height > 0 else 0)
        if coord_space.lower() == "screen":
            pt_sc = wt.POINT(raw_x, raw_y)
            user32.ScreenToClient(hwnd, ctypes.byref(pt_sc))
            cx, cy = int(pt_sc.x), int(pt_sc.y)
        else:
            cx, cy = raw_x, raw_y

    if bounds_check and explicit_xy:
        if width <= 0 or height <= 0 or cx < 0 or cy < 0 or cx >= width or cy >= height:
            pt_after = get_physical_cursor_pos()
            return {
                "ok": False,
                "status": "OUT_OF_BOUNDS",
                "hwnd": int(hwnd),
                "target_hwnd": int(hwnd),
                "client_xy": [cx, cy],
                "bounds": {"width": width, "height": height},
                "physical_cursor_delta_px": [
                    pt_after[0] - pt_before[0],
                    pt_after[1] - pt_before[1],
                ],
                "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            }

    target_hwnd = int(hwnd)
    target_x, target_y = cx, cy
    if resolve_child and explicit_xy:
        target_hwnd, target_x, target_y = _resolve_child_at_client_point(hwnd, cx, cy)

    cls_name = _get_class_name(target_hwnd).lower()
    method_used = ""
    if btn_norm == "left" and not double and use_uia and ("button" in cls_name or not explicit_xy):
        if not async_post:
            uia_method = _try_uia_invoke(target_hwnd)
            if uia_method:
                method_used = uia_method
        if not method_used and "button" in cls_name:
            _send_msg(target_hwnd, BM_CLICK, 0, 0, async_post=async_post)
            method_used = "UIA_Invoke_BM_CLICK"

    if not method_used:
        lparam = pack_lparam(target_x, target_y)
        if btn_norm == "left":
            down_msg, up_msg, dbl_msg, mk = (
                WM_LBUTTONDOWN,
                WM_LBUTTONUP,
                WM_LBUTTONDBLCLK,
                MK_LBUTTON,
            )
        elif btn_norm == "right":
            down_msg, up_msg, dbl_msg, mk = (
                WM_RBUTTONDOWN,
                WM_RBUTTONUP,
                WM_RBUTTONDBLCLK,
                MK_RBUTTON,
            )
        else:
            down_msg, up_msg, dbl_msg, mk = (
                WM_MBUTTONDOWN,
                WM_MBUTTONUP,
                WM_MBUTTONDBLCLK,
                MK_MBUTTON,
            )

        _send_msg(target_hwnd, WM_MOUSEMOVE, 0, lparam, async_post=async_post)
        _send_msg(target_hwnd, down_msg, mk, lparam, async_post=async_post)
        _send_msg(target_hwnd, up_msg, 0, lparam, async_post=async_post)
        if double:
            _send_msg(target_hwnd, dbl_msg, mk, lparam, async_post=async_post)
            _send_msg(target_hwnd, up_msg, 0, lparam, async_post=async_post)
        method_used = f"Win32_WM_{btn_norm.upper()}BUTTON{'DBLCLK' if double else 'CLICK'}"

    pt_after = get_physical_cursor_pos()
    return {
        "ok": True,
        "status": "OK",
        "hwnd": int(hwnd),
        "target_hwnd": int(target_hwnd),
        "class_name": _get_class_name(target_hwnd),
        "method": method_used,
        "button": btn_norm,
        "double": bool(double),
        "client_xy": [target_x, target_y],
        "physical_cursor_delta_px": [pt_after[0] - pt_before[0], pt_after[1] - pt_before[1]],
        "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def ghost_type(
    hwnd: int,
    text: str,
    use_uia: bool = True,
    clear_first: bool = False,
    async_post: bool = False,
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    pt_before = get_physical_cursor_pos()
    if sys.platform != "win32":
        return _posix_ghost_type_fallback(hwnd, text, t0)
    if not hwnd or not user32.IsWindow(hwnd):
        return {
            "ok": False,
            "status": "INVALID_HWND",
            "hwnd": int(hwnd),
            "physical_cursor_delta_px": [0, 0],
            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    method_used = ""
    if clear_first and use_uia:
        if not async_post and _try_uia_set_value(hwnd, text):
            method_used = "UIA_ValuePattern_SetValue"
        else:
            val_buf = ctypes.create_unicode_buffer(text)
            res_out = ctypes.c_size_t(0)
            ok = user32.SendMessageTimeoutW(
                hwnd,
                WM_SETTEXT,
                0,
                ctypes.addressof(val_buf),
                SMTO_ABORTIFHUNG,
                500,
                ctypes.byref(res_out),
            )
            if ok and res_out.value != 0:
                method_used = "UIA_ValuePattern_WM_SETTEXT"

    if not method_used:
        res_out = ctypes.c_size_t(0)
        if clear_first:
            empty_buf = ctypes.create_unicode_buffer("")
            user32.SendMessageTimeoutW(
                hwnd,
                WM_SETTEXT,
                0,
                ctypes.addressof(empty_buf),
                SMTO_ABORTIFHUNG,
                500,
                ctypes.byref(res_out),
            )
        else:
            user32.SendMessageTimeoutW(
                hwnd, EM_SETSEL, 0xFFFF, 0xFFFF, SMTO_ABORTIFHUNG, 500, ctypes.byref(res_out)
            )
        for ch in text:
            _send_msg(hwnd, WM_CHAR, ord(ch), 0, async_post=async_post)
        method_used = "Win32_WM_CHAR_Cleared" if clear_first else "Win32_WM_CHAR"

    pt_after = get_physical_cursor_pos()
    return {
        "ok": True,
        "status": "OK",
        "hwnd": int(hwnd),
        "method": method_used,
        "chars_sent": len(text),
        "clear_first": bool(clear_first),
        "physical_cursor_delta_px": [pt_after[0] - pt_before[0], pt_after[1] - pt_before[1]],
        "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def ghost_scroll(
    hwnd: int,
    delta: int = 120,
    x: int = 0,
    y: int = 0,
    horizontal: bool = False,
    async_post: bool = False,
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    pt_before = get_physical_cursor_pos()
    if sys.platform != "win32" or not hwnd or not user32.IsWindow(hwnd):
        return {
            "ok": False,
            "status": "INVALID_HWND",
            "hwnd": int(hwnd),
            "physical_cursor_delta_px": [0, 0],
            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }
    screen_pt = wt.POINT(int(x), int(y))
    user32.ClientToScreen(hwnd, ctypes.byref(screen_pt))
    lparam = pack_lparam(int(screen_pt.x), int(screen_pt.y))
    wparam = (int(delta) & 0xFFFF) << 16
    msg = WM_MOUSEHWHEEL if horizontal else WM_MOUSEWHEEL
    _send_msg(hwnd, msg, wparam, lparam, async_post=async_post)
    pt_after = get_physical_cursor_pos()
    return {
        "ok": True,
        "status": "OK",
        "hwnd": int(hwnd),
        "method": "Win32_WM_MOUSEHWHEEL" if horizontal else "Win32_WM_MOUSEWHEEL",
        "delta": int(delta),
        "horizontal": bool(horizontal),
        "client_xy": [int(x), int(y)],
        "physical_cursor_delta_px": [pt_after[0] - pt_before[0], pt_after[1] - pt_before[1]],
        "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def ghost_window_cmd(
    hwnd: int,
    action: str = "maximize",
    async_post: bool = False,
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    pt_before = get_physical_cursor_pos()
    act_norm = action.lower().strip()
    sc_map = {
        "maximize": SC_MAXIMIZE,
        "minimize": SC_MINIMIZE,
        "restore": SC_RESTORE,
    }
    if act_norm not in sc_map:
        return {
            "ok": False,
            "status": "INVALID_ACTION",
            "hwnd": int(hwnd),
            "physical_cursor_delta_px": [0, 0],
            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }
    if sys.platform != "win32" or not hwnd or not user32.IsWindow(hwnd):
        return {
            "ok": False,
            "status": "INVALID_HWND",
            "hwnd": int(hwnd),
            "physical_cursor_delta_px": [0, 0],
            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }
    _send_msg(hwnd, WM_SYSCOMMAND, sc_map[act_norm], 0, async_post=async_post)
    pt_after = get_physical_cursor_pos()
    return {
        "ok": True,
        "status": "OK",
        "hwnd": int(hwnd),
        "action": act_norm,
        "method": f"Win32_WM_SYSCOMMAND_{act_norm.upper()}",
        "physical_cursor_delta_px": [pt_after[0] - pt_before[0], pt_after[1] - pt_before[1]],
        "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def _posix_ghost_click_fallback(
    hwnd: int,
    x: Optional[int],
    y: Optional[int],
    button: str,
    double: bool,
    t0: float,
) -> Dict[str, Any]:
    cx = int(x or 0)
    cy = int(y or 0)
    if sys.platform == "darwin" and shutil.which("osascript"):
        script = f'tell application "System Events" to click at {{{cx}, {cy}}}'
        subprocess.run(
            ["osascript", "-e", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return {
            "ok": True,
            "status": "OK",
            "hwnd": int(hwnd),
            "target_hwnd": int(hwnd),
            "method": "macOS_AX_SystemEvents",
            "button": button,
            "double": bool(double),
            "client_xy": [cx, cy],
            "physical_cursor_delta_px": [0, 0],
            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }
    if shutil.which("xdotool"):
        btn_code = {"left": "1", "middle": "2", "right": "3"}.get(button, "1")
        cmd: List[str] = ["xdotool", "mousemove", "--window", str(hwnd), str(cx), str(cy), "click"]
        if double:
            cmd.extend(["--repeat", "2"])
        cmd.extend(["--window", str(hwnd), btn_code])
        subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return {
            "ok": True,
            "status": "OK",
            "hwnd": int(hwnd),
            "target_hwnd": int(hwnd),
            "method": "Linux_XSendEvent_xdotool",
            "button": button,
            "double": bool(double),
            "client_xy": [cx, cy],
            "physical_cursor_delta_px": [0, 0],
            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }
    return {
        "ok": False,
        "status": "UNSUPPORTED_PLATFORM",
        "hwnd": int(hwnd),
        "physical_cursor_delta_px": [0, 0],
        "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def _posix_ghost_type_fallback(hwnd: int, text: str, t0: float) -> Dict[str, Any]:
    if shutil.which("xdotool"):
        subprocess.run(
            ["xdotool", "type", "--window", str(hwnd), "--", text],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        return {
            "ok": True,
            "status": "OK",
            "hwnd": int(hwnd),
            "method": "Linux_XSendEvent_xdotool_type",
            "chars_sent": len(text),
            "physical_cursor_delta_px": [0, 0],
            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }
    return {
        "ok": False,
        "status": "UNSUPPORTED_PLATFORM",
        "hwnd": int(hwnd),
        "physical_cursor_delta_px": [0, 0],
        "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


def compute_som_grid(
    width: int,
    height: int,
    grid_cols: int = 12,
    grid_rows: int = 8,
    origin_screen_xy: Tuple[int, int] = (0, 0),
) -> Dict[str, Dict[str, Any]]:
    cols = max(1, int(grid_cols))
    rows = max(1, int(grid_rows))
    w = max(1, int(width))
    h = max(1, int(height))
    ox, oy = int(origin_screen_xy[0]), int(origin_screen_xy[1])
    cells: Dict[str, Dict[str, Any]] = {}
    cell_id = 1
    for r in range(rows):
        y0 = (r * h) // rows
        y1 = ((r + 1) * h) // rows
        ch = y1 - y0
        cy = y0 + ch // 2
        for c in range(cols):
            x0 = (c * w) // cols
            x1 = ((c + 1) * w) // cols
            cw = x1 - x0
            cx = x0 + cw // 2
            cells[str(cell_id)] = {
                "cell_id": cell_id,
                "row": r,
                "col": c,
                "client_bbox": [x0, y0, x1, y1],
                "width": cw,
                "height": ch,
                "area": cw * ch,
                "client_xy": [cx, cy],
                "screen_xy": [ox + cx, oy + cy],
            }
            cell_id += 1
    return cells


def resolve_som_cell(cells_or_manifest: Dict[str, Any], cell_id: int) -> Dict[str, Any]:
    cells = cells_or_manifest.get("cells", cells_or_manifest)
    key = str(int(cell_id))
    if key not in cells:
        valid_ids = [int(k) for k in cells.keys() if str(k).isdigit()]
        min_id = min(valid_ids) if valid_ids else 1
        max_id = max(valid_ids) if valid_ids else 0
        return {
            "ok": False,
            "status": "OUT_OF_BOUNDS",
            "error": f"SoM cell_id {cell_id} outside valid range [{min_id}, {max_id}].",
            "cell_id": int(cell_id),
        }
    entry = cells[key]
    return {
        "ok": True,
        "status": "OK",
        "cell_id": int(cell_id),
        "client_xy": list(entry["client_xy"]),
        "screen_xy": list(entry["screen_xy"]),
        "client_bbox": list(entry["client_bbox"]),
    }


def _hex_to_rgb(color_hex: str) -> Tuple[int, int, int]:
    clean = color_hex.lstrip("#")
    if len(clean) == 6:
        return (int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16))
    return (37, 99, 235)


@dataclass
class AgentCursorState:
    agent_id: str
    x: int
    y: int
    color_hex: str = "#2563EB"
    label: str = ""
    ripple_radius: int = 0
    updated_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if not d["label"]:
            d["label"] = self.agent_id
        return d


def render_hud_preview(
    base_image_or_size: Union["Image.Image", Tuple[int, int]],
    cursors: List[Union[AgentCursorState, Dict[str, Any]]],
) -> "Image.Image":
    if isinstance(base_image_or_size, Image.Image):
        canvas = base_image_or_size.copy().convert("RGBA")
    else:
        w, h = int(base_image_or_size[0]), int(base_image_or_size[1])
        canvas = Image.new("RGBA", (w, h), (248, 250, 252, 255))

    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for idx, raw_cur in enumerate(cursors):
        c_dict = raw_cur.to_dict() if isinstance(raw_cur, AgentCursorState) else dict(raw_cur)
        agent_id = str(c_dict.get("agent_id", f"Agent-{idx + 1}"))
        x = int(c_dict.get("x", 0))
        y = int(c_dict.get("y", 0))
        color_hex = str(
            c_dict.get(
                "color_hex",
                AGENT_PALETTE.get(agent_id, DEFAULT_COLOR_LIST[idx % len(DEFAULT_COLOR_LIST)]),
            )
        )
        label = str(c_dict.get("label") or agent_id)
        ripple = int(c_dict.get("ripple_radius", 18))
        r, g, b = _hex_to_rgb(color_hex)

        if ripple > 0:
            draw.ellipse([x - ripple, y - ripple, x + ripple, y + ripple], outline=(r, g, b, 190), width=2)
            inner_r = max(4, ripple // 2)
            draw.ellipse([x - inner_r, y - inner_r, x + inner_r, y + inner_r], outline=(r, g, b, 235), width=2)

        arrow_pts = [
            (x, y),
            (x, y + 18),
            (x + 5, y + 14),
            (x + 9, y + 21),
            (x + 12, y + 19),
            (x + 8, y + 12),
            (x + 14, y + 12),
        ]
        draw.polygon(arrow_pts, fill=(r, g, b, 255), outline=(255, 255, 255, 255))
        tag_x, tag_y = x + 16, y + 12
        tag_w = max(52, len(label) * 6 + 14)
        draw.rectangle(
            [tag_x, tag_y, tag_x + tag_w, tag_y + 18],
            fill=(r, g, b, 240),
            outline=(255, 255, 255, 255),
            width=1,
        )
        draw.text((tag_x + 6, tag_y + 3), label, fill=(255, 255, 255, 255))

    return Image.alpha_composite(canvas, overlay).convert("RGB")


def capture_window_image(hwnd: int, client_only: bool = True) -> Tuple["Image.Image", str]:
    if sys.platform != "win32" or not hwnd or not user32.IsWindow(hwnd):
        return (Image.new("RGB", (400, 300), (248, 250, 252)), "synthetic_fallback")
    rc = wt.RECT()
    if client_only:
        user32.GetClientRect(hwnd, ctypes.byref(rc))
    else:
        user32.GetWindowRect(hwnd, ctypes.byref(rc))
    w = max(1, int(rc.right - rc.left))
    h = max(1, int(rc.bottom - rc.top))
    hdc_win = user32.GetDC(hwnd) if client_only else user32.GetWindowDC(hwnd)
    if not hdc_win:
        return (Image.new("RGB", (w, h), (248, 250, 252)), "synthetic_fallback")

    hdc_mem = 0
    hbmp = 0
    old_obj = 0
    try:
        hdc_mem = gdi32.CreateCompatibleDC(hdc_win)
        hbmp = gdi32.CreateCompatibleBitmap(hdc_win, w, h)
        old_obj = gdi32.SelectObject(hdc_mem, hbmp)

        method = "Win32_PrintWindow"
        pw_flags = (PW_CLIENTONLY | PW_RENDERFULLCONTENT) if client_only else PW_RENDERFULLCONTENT
        ok = bool(user32.PrintWindow(hwnd, hdc_mem, pw_flags))
        if not ok:
            ok = bool(user32.PrintWindow(hwnd, hdc_mem, PW_CLIENTONLY if client_only else 0))
        if not ok:
            gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_win, 0, 0, SRCCOPY)
            method = "Win32_BitBlt"

        bmi = BITMAPINFO()
        bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
        bmi.bmiHeader.biWidth = w
        bmi.bmiHeader.biHeight = -h
        bmi.bmiHeader.biPlanes = 1
        bmi.bmiHeader.biBitCount = 32
        bmi.bmiHeader.biCompression = BI_RGB

        raw_buf = ctypes.create_string_buffer(w * h * 4)
        gdi32.GetDIBits(hdc_mem, hbmp, 0, h, raw_buf, ctypes.byref(bmi), DIB_RGB_COLORS)
    finally:
        if hdc_mem and old_obj:
            gdi32.SelectObject(hdc_mem, old_obj)
        if hbmp:
            gdi32.DeleteObject(hbmp)
        if hdc_mem:
            gdi32.DeleteDC(hdc_mem)
        user32.ReleaseDC(hwnd, hdc_win)

    img = Image.frombuffer("RGBA", (w, h), raw_buf, "raw", "BGRA", 0, 1).convert("RGB")
    return (img, method)


def capture_som(
    hwnd: int,
    output_path: str,
    grid_cols: int = 12,
    grid_rows: int = 8,
    draw_controls: bool = True,
    cursors: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    if sys.platform == "win32" and (not hwnd or not user32.IsWindow(hwnd)):
        return {
            "ok": False,
            "status": "INVALID_HWND",
            "error": f"Window handle {hwnd} is not a valid live HWND.",
            "hwnd": int(hwnd),
            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }
    base_img, cap_method = capture_window_image(hwnd, client_only=True)
    w, h = base_img.size
    tree = inspect_window(hwnd, visible_only=True)
    controls = tree.get("controls", []) if tree.get("ok") else []

    ox, oy = 0, 0
    if sys.platform == "win32" and hwnd and user32.IsWindow(hwnd):
        pt0 = wt.POINT(0, 0)
        user32.ClientToScreen(hwnd, ctypes.byref(pt0))
        ox, oy = int(pt0.x), int(pt0.y)

    cells = compute_som_grid(w, h, grid_cols=grid_cols, grid_rows=grid_rows, origin_screen_xy=(ox, oy))
    annotated = base_img.convert("RGBA")
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    for cell in cells.values():
        x0, y0, x1, y1 = cell["client_bbox"]
        draw.rectangle([x0, y0, x1 - 1, y1 - 1], outline=(15, 23, 42, 95), width=1)
        tag = str(cell["cell_id"])
        tw = max(14, len(tag) * 6 + 4)
        draw.rectangle([x0 + 1, y0 + 1, min(x1 - 1, x0 + tw), min(y1 - 1, y0 + 12)], fill=(15, 23, 42, 175))
        draw.text((x0 + 3, y0 + 1), tag, fill=(248, 250, 252, 245))

    marked_controls = 0
    if draw_controls:
        for ctrl in controls:
            crc = ctrl["client_rect"]
            cx0 = max(0, min(w - 1, int(crc["left"])))
            cy0 = max(0, min(h - 1, int(crc["top"])))
            cx1 = max(0, min(w - 1, int(crc["right"])))
            cy1 = max(0, min(h - 1, int(crc["bottom"])))
            if cx1 <= cx0 or cy1 <= cy0:
                continue
            draw.rectangle([cx0, cy0, cx1, cy1], outline=(37, 99, 235, 230), width=2)
            c_label = f"#C{ctrl['id']}"
            bw = len(c_label) * 6 + 6
            draw.rectangle([cx0, max(0, cy0 - 13), min(w - 1, cx0 + bw), cy0], fill=(37, 99, 235, 235))
            draw.text((cx0 + 3, max(0, cy0 - 12)), c_label, fill=(255, 255, 255, 255))
            marked_controls += 1

    comp = Image.alpha_composite(annotated, overlay).convert("RGB")
    if cursors:
        comp = render_hud_preview(comp, cursors)

    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)
    comp.save(str(out_file), format="PNG")

    manifest_file = out_file.with_name(f"{out_file.stem}_som_manifest.json")
    manifest_payload = {
        "ok": True,
        "hwnd": int(hwnd),
        "title": tree.get("title", ""),
        "image_path": str(out_file),
        "manifest_path": str(manifest_file),
        "capture_method": cap_method,
        "width": w,
        "height": h,
        "window_area": w * h,
        "total_cell_area": sum(c["area"] for c in cells.values()),
        "grid_cols": int(grid_cols),
        "grid_rows": int(grid_rows),
        "cell_count": len(cells),
        "controls_marked": marked_controls,
        "controls": controls,
        "cells": cells,
        "latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }
    manifest_file.write_text(json.dumps(manifest_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest_payload


def physical_move_with_reflex(
    target_x: int,
    target_y: int,
    duration_ms: float = 60.0,
    step_ms: float = 2.0,
    tolerance_px: int = 4,
    corner_failsafe: bool = True,
    failsafe_xy: Tuple[int, int] = (0, 0),
    simulated_interrupt_at_step: Optional[int] = None,
    simulated_interrupt_delta: Tuple[int, int] = (24, 24),
    start_xy: Optional[Tuple[int, int]] = None,
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    sx, sy = start_xy if start_xy is not None else get_physical_cursor_pos()
    tx, ty = int(target_x), int(target_y)
    fx, fy = int(failsafe_xy[0]), int(failsafe_xy[1])

    if corner_failsafe and ((tx == fx and ty == fy) or (start_xy is not None and sx == fx and sy == fy)):
        return {
            "ok": False,
            "completed": False,
            "yielded": True,
            "reason": "emergency_corner_failsafe",
            "steps_executed": 0,
            "total_steps": 0,
            "displacement_px": 0.0,
            "reaction_latency_ms": round((time.perf_counter() - t0) * 1000.0, 3),
            "start_xy": [sx, sy],
            "final_xy": [sx, sy],
        }

    dx, dy = tx - sx, ty - sy
    if dx == 0 and dy == 0:
        return {
            "ok": True,
            "completed": True,
            "yielded": False,
            "reason": "equilibrium_zero_delta",
            "steps_executed": 0,
            "total_steps": 0,
            "displacement_px": 0.0,
            "reaction_latency_ms": 0.0,
            "start_xy": [sx, sy],
            "final_xy": [sx, sy],
        }

    step_dt_ms = max(0.5, min(4.0, float(step_ms)))
    total_steps = max(2, int(math.ceil(max(4.0, float(duration_ms)) / step_dt_ms)))
    tol = max(1, int(tolerance_px))

    last_cmd_x, last_cmd_y = sx, sy
    test_x = sx if (sx != 0 or sy != 0) else 16
    test_y = sy if (sx != 0 or sy != 0) else 16
    if sys.platform == "win32":
        user32.SetCursorPos(test_x, test_y)
    probe_x, probe_y = get_physical_cursor_pos()
    hw_writable = abs(probe_x - test_x) <= tol and abs(probe_y - test_y) <= tol
    if hw_writable and sys.platform == "win32" and (test_x != sx or test_y != sy):
        user32.SetCursorPos(sx, sy)
        probe_x, probe_y = get_physical_cursor_pos()

    for step_idx in range(1, total_steps + 1):
        t_step = time.perf_counter()
        raw_x, raw_y = get_physical_cursor_pos()
        if (
            corner_failsafe
            and hw_writable
            and (last_cmd_x != fx or last_cmd_y != fy)
            and raw_x == fx
            and raw_y == fy
        ):
            react_ms = (time.perf_counter() - t_step) * 1000.0
            return {
                "ok": False,
                "completed": False,
                "yielded": True,
                "reason": "emergency_corner_failsafe",
                "steps_executed": step_idx - 1,
                "total_steps": total_steps,
                "displacement_px": round(math.hypot(last_cmd_x - sx, last_cmd_y - sy), 3),
                "reaction_latency_ms": round(react_ms, 3),
                "start_xy": [sx, sy],
                "final_xy": [raw_x, raw_y],
            }
        if hw_writable:
            cur_x, cur_y = raw_x, raw_y
        else:
            cur_x = last_cmd_x + (raw_x - probe_x)
            cur_y = last_cmd_y + (raw_y - probe_y)

        if simulated_interrupt_at_step is not None and step_idx >= int(simulated_interrupt_at_step):
            cur_x = last_cmd_x + int(simulated_interrupt_delta[0])
            cur_y = last_cmd_y + int(simulated_interrupt_delta[1])

        human_delta = max(abs(cur_x - last_cmd_x), abs(cur_y - last_cmd_y))
        if human_delta > tol:
            react_ms = (time.perf_counter() - t_step) * 1000.0
            return {
                "ok": True,
                "completed": False,
                "yielded": True,
                "reason": "human_reflex_interrupt",
                "human_delta_px": int(human_delta),
                "tolerance_px": tol,
                "steps_executed": step_idx - 1,
                "total_steps": total_steps,
                "displacement_px": round(math.hypot(last_cmd_x - sx, last_cmd_y - sy), 3),
                "reaction_latency_ms": round(react_ms, 3),
                "start_xy": [sx, sy],
                "final_xy": [cur_x, cur_y],
            }

        alpha = step_idx / float(total_steps)
        smooth = alpha * alpha * (3.0 - 2.0 * alpha)
        next_x = int(round(sx + dx * smooth))
        next_y = int(round(sy + dy * smooth))
        if sys.platform == "win32":
            user32.SetCursorPos(next_x, next_y)
        last_cmd_x, last_cmd_y = next_x, next_y
        if step_idx < total_steps:
            time.sleep(step_dt_ms / 1000.0)

    return {
        "ok": True,
        "completed": True,
        "yielded": False,
        "reason": "completed",
        "steps_executed": total_steps,
        "total_steps": total_steps,
        "displacement_px": round(math.hypot(tx - sx, ty - sy), 3),
        "reaction_latency_ms": 0.0,
        "start_xy": [sx, sy],
        "final_xy": [tx, ty],
    }


def run_self_test() -> Dict[str, Any]:
    """
    Execute the Bidirectional Counter-Anchor (`A_pos ∧ A_neg`) and `UL-01..UL-08`
    verification suite for `/xmouse` including Multi-Display & Negative-Monitor verification.
    """
    # 1. UL-01 & UL-04 SoM Grid Conservation & Bounds Check (with negative monitor origin)
    cells = compute_som_grid(493, 317, grid_cols=12, grid_rows=8, origin_screen_xy=(-1920, -431))
    area_conserved = sum(c["area"] for c in cells.values()) == 493 * 317
    pos_cell = resolve_som_cell(cells, 1)
    neg_cell = resolve_som_cell(cells, 999)

    # 2. UL-03 Equilibrium, Negative Monitor Trajectory & UL-05 Reflex Yield Counter-Anchors
    eq_res = physical_move_with_reflex(150, 150, start_xy=(150, 150))
    pos_reflex = physical_move_with_reflex(180, 180, duration_ms=10.0, step_ms=2.0, start_xy=(150, 150))
    neg_mon_move = physical_move_with_reflex(
        -1920, -300, duration_ms=10.0, step_ms=2.0, start_xy=(-1880, -280)
    )
    neg_reflex = physical_move_with_reflex(
        300,
        300,
        duration_ms=30.0,
        step_ms=2.0,
        tolerance_px=4,
        simulated_interrupt_at_step=2,
        simulated_interrupt_delta=(22, 22),
        start_xy=(150, 150),
    )
    neg_corner = physical_move_with_reflex(0, 0, corner_failsafe=True, start_xy=(150, 150))
    lparam_rt = unpack_lparam(pack_lparam(-1920, -431)) == (-1920, -431)
    mon_res = list_monitors()

    # 3. Invalid HWND negative guard
    neg_hwnd = ghost_click(0, x=10, y=10)

    all_passed = (
        area_conserved
        and pos_cell["ok"] is True
        and neg_cell["status"] == "OUT_OF_BOUNDS"
        and eq_res["displacement_px"] == 0.0
        and pos_reflex["completed"] is True
        and pos_reflex["yielded"] is False
        and neg_mon_move["completed"] is True
        and neg_mon_move["yielded"] is False
        and neg_reflex["yielded"] is True
        and neg_reflex["reaction_latency_ms"] < 10.0
        and neg_corner["reason"] == "emergency_corner_failsafe"
        and lparam_rt
        and mon_res["ok"] is True
        and mon_res["count"] >= 1
        and neg_hwnd["status"] == "INVALID_HWND"
    )
    return {
        "ok": all_passed,
        "verdict": "PASS" if all_passed else "FAIL",
        "checks": {
            "ul01_som_bounds_pos_neg": pos_cell["ok"] and neg_cell["status"] == "OUT_OF_BOUNDS",
            "ul01_negative_monitor_move_ok": neg_mon_move["completed"] and not neg_mon_move["yielded"],
            "ul03_equilibrium_zero_delta": eq_res["displacement_px"] == 0.0,
            "ul03_signed_lparam_roundtrip": lparam_rt,
            "ul04_som_area_partition_conservation": area_conserved,
            "ul04_multidisplay_virtual_screen": mon_res["ok"] and mon_res["count"] >= 1,
            "ul05_reflex_a_pos_complete": pos_reflex["completed"] and not pos_reflex["yielded"],
            "ul05_reflex_a_neg_interrupt_lt_10ms": neg_reflex["yielded"]
            and neg_reflex["reaction_latency_ms"] < 10.0,
            "ul05_reflex_a_neg_corner_failsafe": neg_corner["reason"] == "emergency_corner_failsafe",
            "ul08_invalid_hwnd_guard": neg_hwnd["status"] == "INVALID_HWND",
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xmouse_cli",
        description="Universal XMouse Ghost Engine CLI (/xmouse Skill Runner)",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser(
        "monitors",
        help="List all connected display monitors, Virtual Screen bounds, and Per-Monitor DPI v2 scale factors",
    )

    p_win = sub.add_parser("windows", help="List top-level desktop windows (< 2 ms)")
    p_win.add_argument("--all", action="store_true", help="Include invisible background windows")
    p_win.add_argument("--filter", default="", help="Substring filter for window title or class")

    p_insp = sub.add_parser("inspect", help="Inspect UIA & Win32 control hierarchy of a window (< 5 ms)")
    p_insp.add_argument("--hwnd", type=int, required=True, help="Target window HWND")
    p_insp.add_argument("--query", default="", help="Optional control name/class substring filter")
    p_insp.add_argument("--type", default="", help="Optional control_type filter (Button, Edit, etc.)")
    p_insp.add_argument("--patterns", action="store_true", help="Probe live UIAutomationCore patterns")

    p_wcmd = sub.add_parser(
        "window-cmd",
        help="Maximize, minimize, or restore a window via WM_SYSCOMMAND (0.0 px cursor hijack)",
    )
    p_wcmd.add_argument("--hwnd", type=int, required=True, help="Target window HWND")
    p_wcmd.add_argument(
        "--action",
        choices=["maximize", "minimize", "restore"],
        default="maximize",
        help="Window state command",
    )

    p_clk = sub.add_parser("click", help="Send a background Ghost Click (zero physical cursor movement)")
    p_clk.add_argument("--hwnd", type=int, required=True, help="Target window or control HWND")
    p_clk.add_argument("--x", type=int, default=None, help="Client/screen X coordinate")
    p_clk.add_argument("--y", type=int, default=None, help="Client/screen Y coordinate")
    p_clk.add_argument("--button", choices=["left", "right", "middle"], default="left")
    p_clk.add_argument("--double", action="store_true", help="Send double click")
    p_clk.add_argument("--space", choices=["client", "screen"], default="client")

    p_typ = sub.add_parser("type", help="Send background text entry (WM_SETTEXT / WM_CHAR)")
    p_typ.add_argument("--hwnd", type=int, required=True, help="Target Edit/control HWND")
    p_typ.add_argument("--text", required=True, help="Text string to type")
    p_typ.add_argument("--clear", action="store_true", help="Clear existing field text before typing")

    p_scr = sub.add_parser("scroll", help="Send background mouse wheel scroll (WM_MOUSEWHEEL)")
    p_scr.add_argument("--hwnd", type=int, required=True, help="Target window HWND")
    p_scr.add_argument("--delta", type=int, default=120, help="Wheel delta (+120 up, -120 down)")
    p_scr.add_argument("--x", type=int, default=0)
    p_scr.add_argument("--y", type=int, default=0)
    p_scr.add_argument("--horizontal", action="store_true")

    p_som = sub.add_parser("som", help="Capture off-screen window screenshot with Set-of-Mark (SoM) grid")
    p_som.add_argument("--hwnd", type=int, required=True, help="Target window HWND")
    p_som.add_argument("--output", required=True, help="Output PNG path")
    p_som.add_argument("--cols", type=int, default=12, help="Grid columns (default: 12)")
    p_som.add_argument("--rows", type=int, default=8, help="Grid rows (default: 8)")

    p_cell = sub.add_parser("resolve-cell", help="Resolve a 1-based SoM cell_id from a manifest JSON")
    p_cell.add_argument("--manifest", required=True, help="Path to *_som_manifest.json")
    p_cell.add_argument("--cell", type=int, required=True, help="1-based cell_id")

    p_ref = sub.add_parser("reflex-move", help="Move physical mouse with < 10 ms human Reflex Yield")
    p_ref.add_argument("--x", type=int, required=True, help="Target screen X")
    p_ref.add_argument("--y", type=int, required=True, help="Target screen Y")
    p_ref.add_argument("--duration-ms", type=float, default=60.0)
    p_ref.add_argument("--tolerance-px", type=int, default=4)

    sub.add_parser("self-test", help="Run bidirectional counter-anchor (A_pos & A_neg) self-test")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "monitors":
        res = list_monitors()
    elif args.command == "windows":
        res = list_windows(visible_only=not args.all, title_filter=args.filter)
    elif args.command == "inspect":
        if args.query or args.type:
            res = find_controls(args.hwnd, query=args.query, control_type=args.type)
        else:
            res = inspect_window(args.hwnd, include_uia_patterns=args.patterns)
    elif args.command == "window-cmd":
        res = ghost_window_cmd(hwnd=args.hwnd, action=args.action)
    elif args.command == "click":
        res = ghost_click(
            hwnd=args.hwnd,
            x=args.x,
            y=args.y,
            button=args.button,
            double=args.double,
            coord_space=args.space,
        )
    elif args.command == "type":
        res = ghost_type(hwnd=args.hwnd, text=args.text, clear_first=args.clear)
    elif args.command == "scroll":
        res = ghost_scroll(
            hwnd=args.hwnd,
            delta=args.delta,
            x=args.x,
            y=args.y,
            horizontal=args.horizontal,
        )
    elif args.command == "som":
        res = capture_som(hwnd=args.hwnd, output_path=args.output, grid_cols=args.cols, grid_rows=args.rows)
    elif args.command == "resolve-cell":
        manifest_data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
        res = resolve_som_cell(manifest_data, args.cell)
    elif args.command == "reflex-move":
        res = physical_move_with_reflex(
            target_x=args.x,
            target_y=args.y,
            duration_ms=args.duration_ms,
            tolerance_px=args.tolerance_px,
        )
    elif args.command == "self-test":
        res = run_self_test()
    else:
        parser.print_help()
        return 1

    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0 if res.get("ok", True) else 1


if __name__ == "__main__":
    sys.exit(main())
