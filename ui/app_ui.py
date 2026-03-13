import tkinter as tk
from tkinter import ttk
import queue

from configs.config_manager import (
    get_active_selection,
    load_config,
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

        self._build_main()

    def _build_main(self):
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill="both", expand=True)

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x")

        ttk.Button(buttons, text="Debug", command=self.start_debug).pack(side="right", padx=(0, 8))

    def start_debug(self):
        config = load_config()
        platform, game_format = get_active_selection(config)
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
