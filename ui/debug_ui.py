import queue
import tkinter as tk
from tkinter import ttk
from PIL import ImageTk
from configs.config_manager import FORMATS, PLATFORMS
from ui.view_models.debug import DebugUpdateSnapshot
from ui.tk_thread import capture_ui_thread_id, run_on_ui_thread


class DebugWindow:
    POSITION_ORDERS = {
        "HeadsUp": ("SB", "BB"),
        "6-max": ("SB", "BB", "UTG", "HJ", "CO", "BTN"),
    }

    def __init__(
        self,
        parent,
        on_pause_changed,
        on_tick_rate_changed,
        on_game_config_changed,
        on_back_to_main,
        on_exit_app,
        initial_tick_rate,
        initial_platform,
        initial_format,
    ):
        self.parent = parent
        self.on_pause_changed = on_pause_changed
        self.on_tick_rate_changed = on_tick_rate_changed
        self.on_game_config_changed = on_game_config_changed
        self.on_back_to_main = on_back_to_main
        self.on_exit_app = on_exit_app
        self.initial_tick_rate = float(initial_tick_rate)
        self.initial_platform = initial_platform
        self.initial_format = initial_format

        self._running = False
        self._updates = queue.Queue()
        self._ui_thread_id = None

        self.root = None
        self.pause_btn = None
        self.tick_var = None
        self.platform_var = None
        self.format_var = None
        self.platform_combo = None
        self.format_combo = None
        self.state_vars = {}
        self.state_value_labels = []
        self.state_box = None
        self.region_frame = None
        self.region_widgets = {}
        self.region_images = {}
        self.dynamic_positions = {}
        self.paused = False

    def start(self):
        # UI-thread-only: creates the Toplevel and all widgets.
        if self._running:
            return
        self._running = True
        self._ui_thread_id = capture_ui_thread_id()
        self.root = tk.Toplevel(self.parent)
        self.root.title("PokerTool Debug")
        self.root.geometry("1080x700")

        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill="both", expand=True)

        config_box = ttk.LabelFrame(outer, text="Game Config", padding=10)
        config_box.pack(fill="x", pady=(10, 0))

        self.platform_var = tk.StringVar(value=self.initial_platform)
        self.format_var = tk.StringVar(value=self.initial_format)
        ttk.Label(config_box, text="Platform:").grid(row=0, column=0, sticky="w")
        self.platform_combo = ttk.Combobox(
            config_box,
            textvariable=self.platform_var,
            values=PLATFORMS,
            state="readonly",
            width=18,
        )
        self.platform_combo.grid(row=0, column=1, sticky="w", padx=(6, 16))
        ttk.Label(config_box, text="Format:").grid(row=0, column=2, sticky="w")
        self.format_combo = ttk.Combobox(
            config_box,
            textvariable=self.format_var,
            values=FORMATS,
            state="readonly",
            width=18,
        )
        self.format_combo.grid(row=0, column=3, sticky="w", padx=(6, 16))
        self.platform_combo.bind("<<ComboboxSelected>>", self._apply_game_config)
        self.format_combo.bind("<<ComboboxSelected>>", self._apply_game_config)

        self.state_box = ttk.LabelFrame(outer, text="Game State", padding=10)
        self.state_box.pack(fill="x", pady=(10, 0))

        self.state_vars["pot"] = tk.StringVar(value="-")
        self.state_vars["board"] = tk.StringVar(value="-")
        self.state_vars["street"] = tk.StringVar(value="-")
        self._build_state_fields(self.initial_format)

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

    def _toggle_pause(self):
        # UI-thread-only: button callback mutating widgets/state.
        self.paused = not self.paused
        self.pause_btn.configure(text="Resume" if self.paused else "Pause")
        self.on_pause_changed(self.paused)

    def _apply_tick_rate(self):
        # UI-thread-only: reads entry state and updates UI on validation errors.
        try:
            value = float(self.tick_var.get())
            if value < 0.05:
                value = 0.05
                self.tick_var.set(f"{value:.2f}")
            self.on_tick_rate_changed(value)
        except Exception:
            self.tick_var.set(f"{self.initial_tick_rate:.2f}")

    def _apply_game_config(self, _event=None):
        # UI-thread-only: emits selected platform/format to the controller.
        self._build_state_fields(self.format_var.get())
        self.on_game_config_changed(self.platform_var.get(), self.format_var.get())

    def _poll_updates(self):
        # UI-thread-only: drains queued runtime snapshots via Tk after polling.
        latest_payload = None
        while not self._updates.empty():
            latest_payload = self._updates.get_nowait()
        if latest_payload is not None:
            self._apply_update(latest_payload)
        if self._running and self.root is not None:
            self.root.after(120, self._poll_updates)

    def _apply_update(self, payload):
        # UI-thread-only: applies state/image updates to Tk widgets.
        if self.root is None:
            return
        state = payload.state
        for position in self._position_order(self.format_var.get()):
            self.state_vars[position].set(state.position_bets.get(position, "-"))
        self.state_vars["street"].set(state.street)
        self.state_vars["pot"].set(state.pot)
        self.state_vars["board"].set(state.board)

        regions = payload.regions
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
            "bet_2_raw": (1, 0),
            "bet_2_bin": (1, 1),
            "bet_3_raw": (1, 2),
            "bet_3_bin": (1, 3),
            "bet_4_raw": (2, 0),
            "bet_4_bin": (2, 1),
            "bet_5_raw": (2, 2),
            "bet_5_bin": (2, 3),
            "board_0_raw": (3, 0),
            "board_0_bin": (3, 1),
            "pot_0_raw": (4, 0),
            "pot_0_bin": (4, 1),
        }
        return fixed.get(key)

    def _region_position(self, key):
        fixed = self._fixed_region_position(key)
        if fixed is not None:
            return fixed

        if key in self.dynamic_positions:
            return self.dynamic_positions[key]

        idx = len(self.dynamic_positions)
        row = 5 + (idx // 4)
        col = idx % 4
        self.dynamic_positions[key] = (row, col)
        return row, col

    def _build_state_fields(self, game_format):
        for widget in self.state_value_labels:
            widget.destroy()
        self.state_value_labels = []

        for position in self._position_order(game_format):
            self.state_vars.setdefault(position, tk.StringVar(value="-"))

        row = 0
        col = 0
        for position in self._position_order(game_format):
            label = ttk.Label(self.state_box, text=f"{position} Bet:")
            label.grid(row=row, column=col, sticky="w")
            value_label = ttk.Label(self.state_box, textvariable=self.state_vars[position])
            value_label.grid(row=row, column=col + 1, sticky="w", padx=(4, 16))
            self.state_value_labels.extend([label, value_label])
            col += 2
            if col >= 6:
                row += 1
                col = 0

        row += 1
        street_label = ttk.Label(self.state_box, text="Street:")
        street_label.grid(row=row, column=0, sticky="w", pady=(8, 0))
        street_value = ttk.Label(self.state_box, textvariable=self.state_vars["street"])
        street_value.grid(row=row, column=1, sticky="w", padx=(4, 16), pady=(8, 0))
        self.state_value_labels.extend([street_label, street_value])

        row += 1
        pot_label = ttk.Label(self.state_box, text="Pot:")
        pot_label.grid(row=row, column=0, sticky="w", pady=(8, 0))
        pot_value = ttk.Label(self.state_box, textvariable=self.state_vars["pot"])
        pot_value.grid(row=row, column=1, sticky="w", padx=(4, 16), pady=(8, 0))
        self.state_value_labels.extend([pot_label, pot_value])

        board_label = ttk.Label(self.state_box, text="Board:")
        board_label.grid(row=row, column=2, sticky="w", pady=(8, 0))
        board_value = ttk.Label(self.state_box, textvariable=self.state_vars["board"])
        board_value.grid(row=row, column=3, columnspan=3, sticky="w", pady=(8, 0))
        self.state_value_labels.extend([board_label, board_value])

    def _position_order(self, game_format):
        normalized_format = (game_format or "").strip()
        return self.POSITION_ORDERS.get(normalized_format, self.POSITION_ORDERS["HeadsUp"])

    def push_update(self, payload: DebugUpdateSnapshot):
        # Runtime-thread-safe: enqueue-only, no Tk access here.
        if not self._running:
            return
        self._updates.put(payload)

    def _on_close(self):
        # UI-thread-only: window close callback from Tk.
        try:
            self.on_exit_app()
        except Exception:
            pass
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
        self._run_on_ui_thread(self._close_from_ui_thread)
