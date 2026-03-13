import pyautogui


class ScreenCapture:
    @staticmethod
    def screenshot_region(region, overlay=None):
        safe_region = (int(region[0]), int(region[1]), int(region[2]), int(region[3]))
        return pyautogui.screenshot(region=safe_region), safe_region
