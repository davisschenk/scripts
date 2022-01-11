import win32gui
import win32con
import win32process
import time
import psutil
import argparse

CLASS_NAME = "JagWindow"
WINDOW_NAME = "RuneScape"
EXE_NAME = "rs2client.exe"
SLEEP_TIME = 5

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", default=WINDOW_NAME, help="Match by title of window")
    parser.add_argument("--cls", default=CLASS_NAME, help="Match by class of window")
    parser.add_argument("--exe", default=EXE_NAME, help="Match by executable name")
    parser.add_argument("--sleep", default=SLEEP_TIME, help="Time inbetween checking windows to minimize")
    parser.add_argument("--verbose", '-v', action="count", default=0, help="Print data about all windows")
    parser.add_argument("-c", help="Disable checking if window is active", default=False, action="store_true")
    args = parser.parse_args()

    def window_callback(hwnd, ctx):
        if args.c or win32gui.IsWindow(hwnd) and win32gui.IsWindowEnabled(hwnd) and win32gui.IsWindowVisible(hwnd):
            process_exe = psutil.Process(win32process.GetWindowThreadProcessId(hwnd)[-1]).name()
            process_cls = win32gui.GetClassName(hwnd)
            process_name = win32gui.GetWindowText(hwnd)
            if args.verbose > 0:
                print(f"{hwnd} {process_exe} - {process_name} ({process_cls})")
            if process_name == args.title or process_cls == args.cls or process_exe == args.exe:
                win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)

    while True:
        win32gui.EnumWindows(window_callback, None)
        time.sleep(SLEEP_TIME)