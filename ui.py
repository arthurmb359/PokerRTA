import tkinter as tk
from tkinter import ttk, messagebox

from TableScrapper import TableScrapper
from config_manager import (
    FORMATS,
    PLATFORMS,
    get_active_selection,
    get_calibration,
    get_seat_centers,
    load_config,
    save_config,
    set_active_selection,
    set_calibration,
)


class PokerSolverUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PokerSolver")
        self.root.geometry("420x220")
        self.root.resizable(False, False)

        self.start_requested = False
        self.selected_platform = None
        self.selected_format = None

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

        ttk.Button(buttons, text="Configuracoes", command=self.open_settings).pack(side="left")
        ttk.Button(buttons, text="Iniciar", command=self.start_program).pack(side="right")

        frame.columnconfigure(1, weight=1)

    def start_program(self):
        platform = self.platform_var.get()
        game_format = self.format_var.get()
        set_active_selection(platform, game_format)

        self.start_requested = True
        self.selected_platform = platform
        self.selected_format = game_format
        self.root.destroy()

    def open_settings(self):
        settings = tk.Toplevel(self.root)
        settings.title("Configuracoes")
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
            text="Calibracao: clique topo-esquerdo e depois fundo-direito para cada player.",
            wraplength=420,
            foreground="#333333",
        )
        info.grid(row=2, column=0, columnspan=2, sticky="w", pady=(0, 12))

        def do_calibrate():
            platform = platform_var.get()
            game_format = format_var.get()
            self.run_calibration(platform, game_format)

        def save_and_close():
            self.platform_var.set(platform_var.get())
            self.format_var.set(format_var.get())
            set_active_selection(self.platform_var.get(), self.format_var.get())
            settings.destroy()

        actions = ttk.Frame(frame)
        actions.grid(row=3, column=0, columnspan=2, sticky="ew")
        ttk.Button(actions, text="Calibrar", command=do_calibrate).pack(side="left")
        ttk.Button(actions, text="Salvar", command=save_and_close).pack(side="right")

        frame.columnconfigure(1, weight=1)

    def run_calibration(self, platform: str, game_format: str):
        player_count = len(get_seat_centers(game_format))
        messagebox.showinfo(
            "Calibracao",
            f"Vamos calibrar {player_count} players para {platform} / {game_format}.\n"
            "Primeiro localize a mesa e deixe-a visivel.",
            parent=self.root,
        )

        table = TableScrapper(platform=platform)
        left_edge = table.get_left_edge()
        top_edge = table.get_top_edge()
        print(f"[Calibration] table edge=({left_edge}, {top_edge})")

        calibrated_regions = []
        for index in range(player_count):
            p1 = self.capture_click(
                f"Player {index + 1}/{player_count}: clique no TOPO ESQUERDO da regiao de bet"
            )
            if p1 is None:
                messagebox.showwarning("Calibracao", "Calibracao cancelada.", parent=self.root)
                return

            p2 = self.capture_click(
                f"Player {index + 1}/{player_count}: clique no FUNDO DIREITO da regiao de bet"
            )
            if p2 is None:
                messagebox.showwarning("Calibracao", "Calibracao cancelada.", parent=self.root)
                return

            x1, y1 = min(p1[0], p2[0]), min(p1[1], p2[1])
            x2, y2 = max(p1[0], p2[0]), max(p1[1], p2[1])

            rel = [x1 - left_edge, y1 - top_edge, x2 - left_edge, y2 - top_edge]
            calibrated_regions.append(rel)
            print(f"[Calibration] player={index} abs=({x1},{y1},{x2},{y2}) rel={rel}")

        set_calibration(platform, game_format, calibrated_regions)
        messagebox.showinfo(
            "Calibracao",
            f"Calibracao salva com sucesso para {platform} / {game_format}.",
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
        overlay.bind("<Escape>", on_cancel)
        overlay.grab_set()
        self.root.wait_window(overlay)

        return point["value"]

    def run(self):
        self.root.mainloop()
        return self.start_requested, self.selected_platform, self.selected_format


if __name__ == "__main__":
    app = PokerSolverUI()
    app.run()
