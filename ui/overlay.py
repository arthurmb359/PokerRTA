import threading
import tkinter as tk

from configs.config_manager import get_regions_category
from services.table.calibration_service import update_calibration_region
from services.table.region_mapper import absolute_corners_to_relative, relative_to_absolute_corners


class CalibrationOverlay:
    HANDLE_MARGIN = 8
    MIN_SIZE = 12

    def __init__(self, platform, game_format, table_left, table_top, on_update=None):
        self.platform = platform
        self.game_format = game_format
        self.table_left = int(table_left)
        self.table_top = int(table_top)
        self.on_update = on_update

        self._thread = None
        self._running = False
        self._closed = threading.Event()

        self.root = None
        self.canvas = None
        self.item_map = {}  # rect_id -> {category, index, label_id}
        self.label_to_rect = {}  # label_id -> rect_id
        self.drag_ctx = None
        self._visible = True

    def start(self):
        if self._running:
            return
        self._running = True
        self._closed.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def set_visible(self, visible: bool, timeout=0.2):
        if self.root is None or not self._running:
            return

        done = threading.Event()

        def _apply():
            try:
                if self.root is None:
                    return
                if visible:
                    self.root.deiconify()
                    self.root.lift()
                else:
                    self.root.withdraw()
                self._visible = visible
            finally:
                done.set()

        try:
            self.root.after(0, _apply)
            done.wait(timeout)
        except Exception:
            pass

    def _run(self):
        self.root = tk.Tk()
        self.root.title("Calibration Overlay")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)

        # Transparent background (Windows): only rectangles/text remain visible.
        transparent = "#ff00ff"
        self.root.configure(bg=transparent)
        try:
            self.root.wm_attributes("-transparentcolor", transparent)
        except Exception:
            pass

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{sw}x{sh}+0+0")

        self.canvas = tk.Canvas(self.root, bg=transparent, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self._build_rectangles()

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.root.bind_all("<Escape>", self._on_escape)

        try:
            self.root.mainloop()
        finally:
            self._running = False
            self._closed.set()

    def _build_rectangles(self):
        self._draw_category("bet", "BET")
        self._draw_category("pot", "POT")
        self._draw_category("board", "BOARD")

    def _draw_category(self, category, label_prefix):
        regions = get_regions_category(self.platform, self.game_format, category)
        for idx, rel in enumerate(regions):
            ax1, ay1, ax2, ay2 = relative_to_absolute_corners(
                self.table_left,
                self.table_top,
                rel,
            )

            rect_id = self.canvas.create_rectangle(
                ax1,
                ay1,
                ax2,
                ay2,
                outline="#00ff66",
                width=2,
                fill="#00ff66",
                stipple="gray25",
            )
            text_id = self.canvas.create_text(
                ax1 + 4,
                ay1 - 2,
                text=f"{label_prefix}-{idx + 1}",
                fill="#00ff66",
                anchor="sw",
                font=("Segoe UI", 10, "bold"),
            )
            self.item_map[rect_id] = {
                "category": category,
                "index": idx,
                "label_id": text_id,
            }
            self.label_to_rect[text_id] = rect_id

    def _on_press(self, event):
        item_ids = self.canvas.find_overlapping(event.x, event.y, event.x, event.y)
        rect_id = None
        for item_id in reversed(item_ids):
            if item_id in self.item_map:
                rect_id = item_id
                break
            if item_id in self.label_to_rect:
                rect_id = self.label_to_rect[item_id]
                break

        if rect_id is None:
            self.drag_ctx = None
            return

        x1, y1, x2, y2 = self.canvas.coords(rect_id)
        mode = self._hit_test_mode(event.x, event.y, x1, y1, x2, y2)
        self.drag_ctx = {
            "rect_id": rect_id,
            "mode": mode,
            "press_x": event.x,
            "press_y": event.y,
            "orig": (x1, y1, x2, y2),
        }

    def _on_drag(self, event):
        if not self.drag_ctx:
            return

        rect_id = self.drag_ctx["rect_id"]
        mode = self.drag_ctx["mode"]
        label_id = self.item_map[rect_id]["label_id"]
        x1, y1, x2, y2 = self.drag_ctx["orig"]
        dx = event.x - self.drag_ctx["press_x"]
        dy = event.y - self.drag_ctx["press_y"]

        if mode == "move":
            nx1, ny1, nx2, ny2 = x1 + dx, y1 + dy, x2 + dx, y2 + dy
        else:
            nx1, ny1, nx2, ny2 = x1, y1, x2, y2
            if "w" in mode:
                nx1 = min(x1 + dx, x2 - self.MIN_SIZE)
            if "e" in mode:
                nx2 = max(x2 + dx, x1 + self.MIN_SIZE)
            if "n" in mode:
                ny1 = min(y1 + dy, y2 - self.MIN_SIZE)
            if "s" in mode:
                ny2 = max(y2 + dy, y1 + self.MIN_SIZE)

        self.canvas.coords(rect_id, nx1, ny1, nx2, ny2)
        self.canvas.coords(label_id, nx1 + 4, ny1 - 2)

    def _hit_test_mode(self, px, py, x1, y1, x2, y2):
        left = abs(px - x1) <= self.HANDLE_MARGIN
        right = abs(px - x2) <= self.HANDLE_MARGIN
        top = abs(py - y1) <= self.HANDLE_MARGIN
        bottom = abs(py - y2) <= self.HANDLE_MARGIN

        if top and left:
            return "nw"
        if top and right:
            return "ne"
        if bottom and left:
            return "sw"
        if bottom and right:
            return "se"
        if left:
            return "w"
        if right:
            return "e"
        if top:
            return "n"
        if bottom:
            return "s"
        return "move"

    def _on_release(self, _event):
        if not self.drag_ctx:
            return

        rect_id = self.drag_ctx["rect_id"]
        info = self.item_map[rect_id]
        category = info["category"]
        index = info["index"]

        corners = self.canvas.coords(rect_id)
        rel = absolute_corners_to_relative(self.table_left, self.table_top, tuple(corners))

        regions = update_calibration_region(
            platform=self.platform,
            game_format=self.game_format,
            category=category,
            index=index,
            rel_region=rel,
        )
        if index < len(regions):
            print(f"[Overlay] updated {category}[{index}] -> {rel}")
            if self.on_update is not None:
                self.on_update(category, regions)

        self.drag_ctx = None

    def _on_escape(self, _event=None):
        self._close_from_ui_thread()

    def _close_from_ui_thread(self):
        self._running = False
        if self.root is None:
            return
        try:
            self.root.quit()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        self.root = None

    def stop(self):
        self._running = False
        if self.root is not None:
            done = threading.Event()

            def _close():
                try:
                    self._close_from_ui_thread()
                finally:
                    done.set()

            try:
                self.root.after(0, _close)
                done.wait(0.8)
            except Exception:
                pass

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=1.0)
