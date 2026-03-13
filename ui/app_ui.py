import tkinter as tk
from tkinter import ttk, messagebox
import queue

from configs.config_manager import (
    FORMATS,
    PLATFORMS,
    get_active_selection,
    get_seat_centers,
    load_config,
    set_active_selection,
    set_calibration_category,
)
from services.table.table_scrapper import TableScrapper

CALIBRATION_CATEGORIES = {
    "bet": "Bet",
    "pot": "Pote",
    "board": "Board",
}


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

        ttk.Button(buttons, text="Configurações", command=self.open_settings).pack(side="left")
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

    def open_settings(self):
        settings = tk.Toplevel(self.root)
        settings.title("Configurações")
        settings.geometry("460x250")
        settings.resizable(False, False)

        platform_var = tk.StringVar(value=self.platform_var.get())
        format_var = tk.StringVar(value=self.format_var.get())

        frame = ttk.Frame(settings, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Plataforma:").grid(row=0, column=0, sticky="w", pady=(0, 8))
        platform_combo = ttk.Combobox(frame, textvariable=platform_var, values=PLATFORMS, state="readonly", width=24)
        platform_combo.grid(row=0, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(frame, text="Formato:").grid(row=1, column=0, sticky="w", pady=(0, 12))
        format_combo = ttk.Combobox(frame, textvariable=format_var, values=FORMATS, state="readonly", width=24)
        format_combo.grid(row=1, column=1, sticky="ew", pady=(0, 12))

        info = ttk.Label(
            frame,
            text="Calibração: escolha a categoria e clique topo-esquerdo e fundo-direito.",
            wraplength=420,
            foreground="#333333",
        )
        info.grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 12))

        def do_calibrate(category: str):
            platform = platform_var.get()
            game_format = format_var.get()
            self.run_calibration(platform, game_format, category)

        actions = ttk.Frame(frame)
        actions.grid(row=3, column=0, columnspan=2, sticky="ew")
        ttk.Button(actions, text="Calibrar Bet", command=lambda: do_calibrate("bet")).pack(side="left")
        ttk.Button(actions, text="Calibrar Pote", command=lambda: do_calibrate("pot")).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Calibrar Board", command=lambda: do_calibrate("board")).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="Fechar", command=settings.destroy).pack(side="right")

        frame.columnconfigure(1, weight=1)

    def run_calibration(self, platform: str, game_format: str, category: str):
        if category == "bet":
            target_count = len(get_seat_centers(game_format))
        else:
            target_count = 1

        category_label = CALIBRATION_CATEGORIES.get(category, category)
        messagebox.showinfo(
            "Calibracao",
            f"Vamos calibrar {target_count} região(ões) de {category_label} para {platform} / {game_format}.\n"
            "Primeiro localize a mesa e deixe-a visivel.",
            parent=self.root,
        )

        table = TableScrapper(platform=platform)
        left_edge = table.get_left_edge()
        top_edge = table.get_top_edge()
        print(f"[Calibration] table edge=({left_edge}, {top_edge})")

        calibrated_regions = []
        for index in range(target_count):
            if category == "bet":
                display_name = f"Player {index + 1}/{target_count}"
            else:
                display_name = f"{category_label} {index + 1}/{target_count}"

            p1 = self.capture_click(
                f"{display_name}: clique no TOPO ESQUERDO da região"
            )
            if p1 is None:
                messagebox.showwarning("Calibração", "Calibração cancelada.", parent=self.root)
                return

            p2 = self.capture_click(
                f"{display_name}: clique no FUNDO DIREITO da região"
            )
            if p2 is None:
                messagebox.showwarning("Calibração", "Calibração cancelada.", parent=self.root)
                return

            x1, y1 = min(p1[0], p2[0]), min(p1[1], p2[1])
            x2, y2 = max(p1[0], p2[0]), max(p1[1], p2[1])

            rel = [
                int(x1 - left_edge),
                int(y1 - top_edge),
                int(x2 - left_edge),
                int(y2 - top_edge),
            ]
            calibrated_regions.append(rel)
            print(f"[Calibration] category={category} idx={index} abs=({x1},{y1},{x2},{y2}) rel={rel}")

        set_calibration_category(platform, game_format, category, calibrated_regions)
        set_active_selection(platform, game_format)
        self.platform_var.set(platform)
        self.format_var.set(game_format)
        messagebox.showinfo(
            "Calibração",
            f"Calibração de {category_label} salva com sucesso para {platform} / {game_format}.",
            parent=self.root,
        )

    def capture_click(self, instruction: str):
        point = {"value": None}

        overlay = tk.Toplevel(self.root)
        overlay.attributes("-fullscreen", True)
        overlay.attributes("-topmost", True)
        overlay.attributes("-alpha", 0.28)
        overlay.configure(bg="black")

        label = tk.Label(
            overlay,
            text=instruction + "\n(ESC cancela)",
            fg="white",
            bg="black",
            font=("Segoe UI", 18, "bold"),
        )
        label.pack(padx=20, pady=20)

        def on_click(event):
            point["value"] = (event.x_root, event.y_root)
            overlay.destroy()

        def on_cancel(_event=None):
            point["value"] = None
            overlay.destroy()

        overlay.bind("<Button-1>", on_click)
        # Use bind_all + forced focus so ESC works consistently on fullscreen overlay.
        overlay.bind_all("<Escape>", on_cancel)
        overlay.grab_set()
        overlay.focus_force()
        overlay.lift()
        try:
            self.root.wait_window(overlay)
        finally:
            try:
                overlay.unbind_all("<Escape>")
            except Exception:
                pass

        return point["value"]

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
