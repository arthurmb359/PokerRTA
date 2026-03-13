import tkinter as tk
from tkinter import ttk
import queue

from configs.config_manager import (
    FORMATS,
    PLATFORMS,
    get_active_selection,
    load_config,
    set_active_selection,
)


class PokerToolUI:
    def __init__(self, on_start_run=None, on_start_debug=None, on_exit=None):
        self.on_start_run = on_start_run
        self.on_start_debug = on_start_debug
        self.on_exit = on_exit
        self._closing = False
        self._pending_calls = queue.Queue()

        self.root = tk.Tk()
        self.root.title("PokerTool")
        self.root.geometry("420x220")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self._handle_close)
        self.root.after(50, self._process_pending_calls)

        self.config = load_config()
        current_platform, current_format = get_active_selection(self.config)

        self.platform_var = tk.StringVar(value=current_platform)
        self.format_var = tk.StringVar(value=current_format)

        self._build_main()

    def _build_main(self):
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Plataforma:").grid(row=0, column=0, sticky="w", pady=(0, 8))
        platform_combo = ttk.Combobox(frame, textvariable=self.platform_var, values=PLATFORMS, state="readonly", width=24)
        platform_combo.grid(row=0, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(frame, text="Formato:").grid(row=1, column=0, sticky="w", pady=(0, 16))
        format_combo = ttk.Combobox(frame, textvariable=self.format_var, values=FORMATS, state="readonly", width=24)
        format_combo.grid(row=1, column=1, sticky="ew", pady=(0, 16))

        buttons = ttk.Frame(frame)
        buttons.grid(row=2, column=0, columnspan=2, sticky="ew")

        ttk.Button(buttons, text="Debug", command=self.start_debug).pack(side="right", padx=(0, 8))
        ttk.Button(buttons, text="Iniciar", command=self.start_program).pack(side="right")

        frame.columnconfigure(1, weight=1)

    def _selected_platform_and_format(self):
        platform = self.platform_var.get()
        game_format = self.format_var.get()
        set_active_selection(platform, game_format)
        return platform, game_format

    def start_program(self):
        platform, game_format = self._selected_platform_and_format()
        if self.on_start_run is not None:
            self.on_start_run(platform, game_format)

    def start_debug(self):
        platform, game_format = self._selected_platform_and_format()
        if self.on_start_debug is not None:
            self.on_start_debug(platform, game_format)

    def show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def hide(self):
        self.root.withdraw()

    def call_soon(self, callback, *args):
        self._pending_calls.put((callback, args))

    def _process_pending_calls(self):
        while True:
            try:
                callback, args = self._pending_calls.get_nowait()
            except queue.Empty:
                break
            callback(*args)

        if not self._closing:
            self.root.after(50, self._process_pending_calls)

    def close(self):
        self._closing = True
        try:
            self.root.destroy()
        except Exception:
            pass

    def _handle_close(self):
        if self._closing:
            return
        if self.on_exit is not None:
            self.on_exit()
            return
        self.close()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = PokerToolUI()
    app.run()
