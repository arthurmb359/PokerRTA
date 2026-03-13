import threading


def capture_ui_thread_id() -> int:
    return threading.get_ident()


def run_on_ui_thread(widget, ui_thread_id: int | None, callback) -> None:
    if widget is None:
        return
    if threading.get_ident() == ui_thread_id:
        callback()
        return
    try:
        widget.after(0, callback)
    except Exception:
        pass
