"""
The Minecraft window on Windows: is the player in game, and pressing F3+C for them.

Singleplayer Minecraft writes the player position to disk only when it saves, and it saves when
it pauses (losing focus) or every few minutes. While the map is on another screen the game keeps
the focus, so the live view asks the game itself: F3+C copies "/execute in <dim> run tp @s x y z
yaw pitch" to the clipboard. The keys are sent only while the player is really in game (Minecraft
in front, mouse captured: no chat, sign, book or inventory open), so they never type into a text
field. Everything here is a no-op on other systems.
"""
import ctypes
import sys
import time

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    from ctypes import wintypes

    _user32 = ctypes.WinDLL("user32", use_last_error=True)

    class _CURSORINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("flags", wintypes.DWORD),
                    ("hCursor", wintypes.HANDLE), ("ptScreenPos", wintypes.POINT)]

    class _KEYBDINPUT(ctypes.Structure):
        _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                    ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

    class _MOUSEINPUT(ctypes.Structure):
        _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG), ("mouseData", wintypes.DWORD),
                    ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.c_size_t)]

    class _INPUTUNION(ctypes.Union):
        _fields_ = [("ki", _KEYBDINPUT), ("mi", _MOUSEINPUT)]

    class _INPUT(ctypes.Structure):
        _fields_ = [("type", wintypes.DWORD), ("u", _INPUTUNION)]

    _user32.GetForegroundWindow.restype = wintypes.HWND
    _user32.GetClassNameW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
    _user32.GetWindowTextW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
    _user32.GetCursorInfo.argtypes = (ctypes.POINTER(_CURSORINFO),)
    _user32.GetClipCursor.argtypes = (ctypes.POINTER(wintypes.RECT),)
    _user32.GetWindowRect.argtypes = (wintypes.HWND, ctypes.POINTER(wintypes.RECT))
    _user32.GetAsyncKeyState.restype = ctypes.c_short
    _user32.SendInput.argtypes = (wintypes.UINT, ctypes.POINTER(_INPUT), ctypes.c_int)

_VK_F3, _VK_C, _VK_CONTROL, _VK_MENU = 0x72, 0x43, 0x11, 0x12
_SC_F3, _SC_C = 0x3D, 0x2E
_KEYEVENTF_KEYUP, _KEYEVENTF_SCANCODE = 0x0002, 0x0008
_CURSOR_SHOWING = 0x1


def minecraft_window():
    """Handle of the Minecraft window if it is the one in front, else None."""
    if not IS_WINDOWS:
        return None
    hwnd = _user32.GetForegroundWindow()
    if not hwnd:
        return None
    cls = ctypes.create_unicode_buffer(64)
    title = ctypes.create_unicode_buffer(256)
    _user32.GetClassNameW(hwnd, cls, 64)
    _user32.GetWindowTextW(hwnd, title, 256)
    # Minecraft Java: a GLFW window up to 1.21 ("Minecraft* 1.21.x - Singleplayer"), an SDL one in
    # 26.x ("Minecraft 26.3 - Singleplayer"); the launcher has its own class
    if (cls.value.startswith("GLFW") or cls.value.startswith("SDL")) and title.value.startswith("Minecraft") \
            and "Hidden" not in title.value:
        return hwnd
    return None


def _mouse_captured(hwnd):
    """
    In game the mouse pointer is hidden (the camera follows the mouse); with chat, signs, books,
    inventories or menus open it is visible. The pointer decides: the window may keep the mouse
    clipped in full screen even with a menu open.
    """
    info = _CURSORINFO()
    info.cbSize = ctypes.sizeof(_CURSORINFO)
    if _user32.GetCursorInfo(ctypes.byref(info)):
        return not (info.flags & _CURSOR_SHOWING) or not info.hCursor
    clip, win = wintypes.RECT(), wintypes.RECT()
    if _user32.GetClipCursor(ctypes.byref(clip)) and _user32.GetWindowRect(hwnd, ctypes.byref(win)):
        return (clip.left >= win.left and clip.right <= win.right and clip.top >= win.top
                and clip.bottom <= win.bottom and clip.right - clip.left < 20000)
    return False


def player_in_game():
    """True when Minecraft is in front and nothing is open on top of the game (keys are safe to send)."""
    hwnd = minecraft_window()
    return bool(hwnd) and _mouse_captured(hwnd)


def _held(vk):
    return bool(_user32.GetAsyncKeyState(vk) & 0x8000)


def press_f3_c():
    """Sends F3+C to the window in front. False if not sent (not in game, or the player holds those keys)."""
    if not player_in_game() or any(_held(vk) for vk in (_VK_F3, _VK_C, _VK_CONTROL, _VK_MENU)):
        return False

    def key(scan, up):
        inp = _INPUT(type=1)                        # INPUT_KEYBOARD
        inp.u.ki = _KEYBDINPUT(0, scan, _KEYEVENTF_SCANCODE | (_KEYEVENTF_KEYUP if up else 0), 0, 0)
        return inp

    down = (_INPUT * 2)(key(_SC_F3, False), key(_SC_C, False))
    up = (_INPUT * 2)(key(_SC_C, True), key(_SC_F3, True))
    if _user32.SendInput(2, down, ctypes.sizeof(_INPUT)) != 2:
        return False
    time.sleep(0.04)                                # the game polls the keyboard once per frame
    _user32.SendInput(2, up, ctypes.sizeof(_INPUT))
    return True
