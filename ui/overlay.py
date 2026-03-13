import threading
import tkinter as tk
import keyboard
from ui.view_models.overlay import OverlayUpdateSnapshot
from ui.tk_thread import capture_ui_thread_id, run_on_ui_thread

from services.table.calibration_service import update_calibration_region
from services.table.region_mapper import absolute_corners_to_relative, relative_to_absolute_corners


class CalibrationOverlay:
    HANDLE_MARGIN = 8
    MIN_SIZE = 12

    def __init__(self, parent, view_snapshot, on_update=None):
        self.parent = parent
        self.view_snapshot = view_snapshot
        self.platform = view_snapshot.platform
        self.game_format = view_snapshot.game_format
        self.table_left = int(view_snapshot.table_left)
        self.table_top = int(view_snapshot.table_top)
        self.on_update = on_update

        self._running = False
        self._ui_thread_id = None

        self.root = None
        self.canvas = None
        self.item_map = {}  # rect_id -> {category, index, label_id}
        self.label_to_rect = {}  # label_id -> rect_id
        self.drag_ctx = None
        self._visible = False
        self._hotkey_handle = None

    def start(self):
        # UI-thread-only: creates the Toplevel, canvas, and overlay bindings.
        if self._running:
            return
        self._running = True
        self._ui_thread_id = capture_ui_thread_id()
        self._register_hotkeys()
        self.root = tk.Toplevel(self.parent)
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
        self.root.bind("<Escape>", self._on_escape)
        self.root.withdraw()

    def set_visible(self, visible: bool, timeout=0.2):
        # Cross-thread-safe: visibility changes are applied on the UI thread.
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

        if capture_ui_thread_id() == self._ui_thread_id:
            _apply()
            return

        try:
            self.root.after(0, _apply)
            done.wait(timeout)
        except Exception:
            pass

    def toggle_visibility(self):
        # Cross-thread-safe: hotkey callback may arrive outside the UI thread.
        self.set_visible(not self._visible)

    def _register_hotkeys(self):
        if self._hotkey_handle is not None:
            return
        try:
            self._hotkey_handle = keyboard.add_hotkey("o", self.toggle_visibility, suppress=False)
        except Exception:
            self._hotkey_handle = None

    def _unregister_hotkeys(self):
        if self._hotkey_handle is None:
            return
        try:
            keyboard.remove_hotkey(self._hotkey_handle)
        except Exception:
            pass
        self._hotkey_handle = None

    def _build_rectangles(self):
        # UI-thread-only: creates overlay canvas items.
        for category_snapshot in self.view_snapshot.categories:
            self._draw_category(category_snapshot)

    def _draw_category(self, category_snapshot):
        category = category_snapshot.category
        label_prefix = category_snapshot.label_prefix
        for idx, rel in enumerate(category_snapshot.regions):
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
        # UI-thread-only: pointer event handler.
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
        # UI-thread-only: pointer event handler mutating canvas items.
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
        # UI-thread-only: persists updated geometry after drag completes.
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
                self.on_update(
                    OverlayUpdateSnapshot(
                        category=category,
                        regions=tuple(tuple(region) for region in regions),
                    )
                )

        self.drag_ctx = None

    def _on_escape(self, _event=None):
        # UI-thread-only: Tk key binding callback.
        self._close_from_ui_thread()

    def _close_from_ui_thread(self):
        # UI-thread-only: the only method allowed to destroy the Tk window.
        self._running = False
        if self.root is None:
            return
        try:
            self.root.destroy()
        except Exception:
            pass
        self.root = None
        self._ui_thread_id = None

    def _run_on_ui_thread(self, callback):
        # Cross-thread bridge: schedules Tk work onto the UI thread when needed.
        run_on_ui_thread(self.root, self._ui_thread_id, callback)

    def stop(self):
        # Cross-thread-safe: may be called outside the UI thread.
        self._running = False
        self._unregister_hotkeys()
        self._run_on_ui_thread(self._close_from_ui_thread)
