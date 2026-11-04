from __future__ import annotations
import json
import tempfile
import time
import sys
from pathlib import Path
import tkinter as tk
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
import main

OUT = Path(__file__).resolve().parent
PROFILE = Path(tempfile.mkdtemp(prefix='folio-kbd-v118-'))
DATA = PROFILE / 'Folio' / 'portfolio_data.sqlite3'
DATA.parent.mkdir(parents=True, exist_ok=True)
main.default_data_path = lambda: DATA

root = tk.Tk()
app = main.PortfolioApp(root)
initial_count = len(app.portfolio.projects)
form_ref: list[tk.Toplevel | None] = [None]
focus_history: list[dict] = []
closed_at = [None]

def walk(widget):
    yield widget
    for child in widget.winfo_children():
        yield from walk(child)

def record_focus(event):
    widget = event.widget
    form = form_ref[0]
    if form is None or not form.winfo_exists() or not str(widget).startswith(str(form)):
        return
    try:
        grid_method = getattr(widget, 'grid_info', None)
        grid = grid_method() if grid_method else {}
        row = int(grid.get('row', -1)) if grid else -1
        mapped = bool(widget.winfo_ismapped())
        info = {'path': str(widget), 'class': widget.winfo_class(), 'grid_row': row, 'mapped': mapped}
        if not focus_history or focus_history[-1] != info:
            focus_history.append(info)
    except tk.TclError:
        pass

def snapshot():
    form = form_ref[0]
    state = {'profile': str(PROFILE), 'db': str(DATA), 'initial_project_count': initial_count,
             'project_count': len(app.portfolio.projects),
             'project_titles': [p.title for p in app.portfolio.projects],
             'focus_history': focus_history}
    if form is not None:
        try:
            state['form_exists'] = bool(form.winfo_exists())
            state['form_geometry'] = form.geometry()
            state['form_client_size'] = [form.winfo_width(), form.winfo_height()]
            focus = form.focus_get()
            state['focus'] = str(focus) if focus else None
            state['focus_class'] = focus.winfo_class() if focus else None
            state['focus_grid_row'] = int(focus.grid_info().get('row', -1)) if focus and focus.grid_info() else -1
            state['focus_mapped'] = bool(focus.winfo_ismapped()) if focus else None
            state['canvas_yview'] = next((list(map(float, w.yview())) for w in walk(form)
                                          if isinstance(w, tk.Canvas) and w.winfo_exists()), None)
            state['description_newlines'] = next((w.get('1.0', 'end-1c').count('\n')
                                                  for w in walk(form) if isinstance(w, tk.Text)
                                                  and int(w.grid_info().get('row', -1)) == 3), None)
        except tk.TclError:
            state['form_exists'] = False
    (OUT / 'desktop-keyboard-v118-state.json').write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if state.get('form_exists') is False and len(app.portfolio.projects) > initial_count:
        if closed_at[0] is None:
            closed_at[0] = time.monotonic()
        elif time.monotonic() - closed_at[0] > 1.2:
            root.destroy()
            return
    else:
        closed_at[0] = None
    try:
        root.after(150, snapshot)
    except tk.TclError:
        pass

def open_form():
    app.edit_dialog()
    dialogs = [child for child in root.winfo_children() if isinstance(child, tk.Toplevel)]
    if not dialogs:
        raise RuntimeError('Project form did not open')
    form = dialogs[-1]
    form_ref[0] = form
    form.geometry('720x480+30+30')
    form.update_idletasks()
    form.bind_all('<FocusIn>', record_focus, add='+')
    root.after(80, snapshot)

root.after(900, open_form)
root.after(180000, root.destroy)
root.mainloop()

