import pyautogui


class ScreenCapture:
    @staticmethod
    def screenshot_region(region, overlay=None):
        safe_region = (int(region[0]), int(region[1]), int(region[2]), int(region[3]))
        if overlay is not None:
            overlay.set_visible(False)
        try:
            return pyautogui.screenshot(region=safe_region), safe_region
        finally:
            if overlay is not None:
                overlay.set_visible(True)

