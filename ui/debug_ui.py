import queue
import threading
import tkinter as tk
from tkinter import ttk
from PIL import ImageTk


class DebugWindow:
    def __init__(
        self,
        on_pause_changed,
        on_tick_rate_changed,
        on_back_to_main,
        on_exit_app,
        initial_tick_rate,
    ):
        self.on_pause_changed = on_pause_changed
        self.on_tick_rate_changed = on_tick_rate_changed
        self.on_back_to_main = on_back_to_main
        self.on_exit_app = on_exit_app
        self.initial_tick_rate = float(initial_tick_rate)

        self._thread = None
        self._running = False
        self._updates = queue.Queue()
        self._closed = threading.Event()

        self.root = None
        self.pause_btn = None
        self.tick_var = None
        self.state_vars = {}
        self.region_frame = None
        self.region_widgets = {}
        self.region_images = {}
        self.dynamic_positions = {}
        self.paused = False

    def start(self):
        if self._running:
            return
        self._running = True
        self._closed.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        self.root = tk.Tk()
        self.root.title("PokerRTA Debug")
        self.root.geometry("980x700")

        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill="both", expand=True)

        state_box = ttk.LabelFrame(outer, text="Game State", padding=10)
        state_box.pack(fill="x")

        self.state_vars["sb_bet"] = tk.StringVar(value="-")
        self.state_vars["bb_bet"] = tk.StringVar(value="-")
        self.state_vars["pot"] = tk.StringVar(value="-")
        self.state_vars["board"] = tk.StringVar(value="-")

        ttk.Label(state_box, text="SB Bet:").grid(row=0, column=0, sticky="w")
        ttk.Label(state_box, textvariable=self.state_vars["sb_bet"]).grid(row=0, column=1, sticky="w", padx=(4, 16))
        ttk.Label(state_box, text="BB Bet:").grid(row=0, column=2, sticky="w")
        ttk.Label(state_box, textvariable=self.state_vars["bb_bet"]).grid(row=0, column=3, sticky="w", padx=(4, 16))
        ttk.Label(state_box, text="Pot:").grid(row=0, column=4, sticky="w")
        ttk.Label(state_box, textvariable=self.state_vars["pot"]).grid(row=0, column=5, sticky="w", padx=(4, 16))

        ttk.Label(state_box, text="Board:").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Label(state_box, textvariable=self.state_vars["board"]).grid(row=1, column=1, columnspan=5, sticky="w", pady=(8, 0))

        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(10, 10))

        self.pause_btn = ttk.Button(controls, text="Pause", command=self._toggle_pause)
        self.pause_btn.pack(side="left")

        ttk.Label(controls, text="Game Tick Rate (s):").pack(side="left", padx=(12, 6))
        self.tick_var = tk.StringVar(value=str(self.initial_tick_rate))
        tick_entry = ttk.Entry(controls, textvariable=self.tick_var, width=8)
        tick_entry.pack(side="left")
        tick_entry.bind("<Return>", lambda _e: self._apply_tick_rate())
        ttk.Button(controls, text="Apply", command=self._apply_tick_rate).pack(side="left", padx=(6, 0))
        ttk.Button(controls, text="Back to Main", command=self.on_back_to_main).pack(side="right")
        ttk.Button(controls, text="Exit App", command=self.on_exit_app).pack(side="right", padx=(0, 8))

        regions_box = ttk.LabelFrame(outer, text="Regions", padding=10)
        regions_box.pack(fill="both", expand=True)

        self.region_frame = ttk.Frame(regions_box)
        self.region_frame.pack(fill="both", expand=True)
        for col in range(4):
            self.region_frame.grid_columnconfigure(col, minsize=300)

        self.root.after(100, self._poll_updates)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        try:
            self.root.mainloop()
        finally:
            self._running = False
            self._closed.set()

    def _toggle_pause(self):
        self.paused = not self.paused
        self.pause_btn.configure(text="Resume" if self.paused else "Pause")
        self.on_pause_changed(self.paused)

    def _apply_tick_rate(self):
        try:
            value = float(self.tick_var.get())
            if value < 0.05:
                value = 0.05
                self.tick_var.set(f"{value:.2f}")
            self.on_tick_rate_changed(value)
        except Exception:
            self.tick_var.set(f"{self.initial_tick_rate:.2f}")

    def _poll_updates(self):
        latest_payload = None
        while not self._updates.empty():
            latest_payload = self._updates.get_nowait()
        if latest_payload is not None:
            self._apply_update(latest_payload)
        if self._running and self.root is not None:
            self.root.after(120, self._poll_updates)

    def _apply_update(self, payload):
        if self.root is None:
            return
        state = payload.get("state", {})
        self.state_vars["sb_bet"].set(state.get("sb_bet", "-"))
        self.state_vars["bb_bet"].set(state.get("bb_bet", "-"))
        self.state_vars["pot"].set(state.get("pot", "-"))
        self.state_vars["board"].set(state.get("board", "-"))

        regions = payload.get("regions", {})
        for key in sorted(regions.keys()):
            pil_img = regions[key]
            if pil_img is None:
                continue

            if key not in self.region_widgets:
                row, col = self._region_position(key)
                card = ttk.Frame(self.region_frame, padding=4)
                card.grid(row=row, column=col, sticky="nw", padx=6, pady=6)
                title = ttk.Label(card, text=key)
                title.pack(anchor="w")
                image_label = ttk.Label(card)
                image_label.pack()
                self.region_widgets[key] = image_label

            img = pil_img.copy().convert("RGB")
            img.thumbnail((280, 160))
            tk_img = ImageTk.PhotoImage(img, master=self.root)
            self.region_images[key] = tk_img
            try:
                self.region_widgets[key].configure(image=tk_img)
                self.region_widgets[key].image = tk_img
            except tk.TclError:
                # Widget may have been destroyed while window is closing.
                pass

    @staticmethod
    def _fixed_region_position(key):
        fixed = {
            "bet_0_raw": (0, 0),
            "bet_0_bin": (0, 1),
            "bet_1_raw": (0, 2),
            "bet_1_bin": (0, 3),
            "board_0_raw": (1, 0),
            "board_0_bin": (1, 1),
            "pot_0_raw": (2, 0),
            "pot_0_bin": (2, 1),
        }
        return fixed.get(key)

    def _region_position(self, key):
        fixed = self._fixed_region_position(key)
        if fixed is not None:
            return fixed

        if key in self.dynamic_positions:
            return self.dynamic_positions[key]

        idx = len(self.dynamic_positions)
        row = 2 + (idx // 4)
        col = idx % 4
        self.dynamic_positions[key] = (row, col)
        return row, col

    def push_update(self, state, regions):
        if not self._running:
            return
        self._updates.put({"state": state, "regions": regions})

    def _on_close(self):
        try:
            self.on_exit_app()
        except Exception:
            pass
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
