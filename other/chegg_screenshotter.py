import pyautogui
import time
pyautogui.FAILSAFE = False
x1 = 2332
y1 = 341
x2 = 3540
y2 = 2060

if __name__ == "__main__":
    page = 0
    print(pyautogui.size())
    for i in range(377):
        im = pyautogui.screenshot(region=(x1, y1, x2-x1, y2-y1))
        im.save(f"out/{page:03}.png")
        page += 1
        pyautogui.move(3377, 787)
        pyautogui.click()
        pyautogui.press("right")
        time.sleep(4)
