# -*- coding: utf-8 -*-
"""Captura la vista ChapterManagerView rediseñada como PNG."""
import customtkinter as ctk
from models.book import Book
from models.chapter import Chapter
from ui.views.chapter_manager_view import ChapterManagerView

libro = Book(name="Juanito")
for t, ts in [
    ("Miku test", "2026-08-19 18:12:56"),
    ("sdasdasdas", "2026-08-20 07:02:32"),
    ("dasdasdaxczfserfsdzcs", "2026-08-20 07:02:32"),
    ("Capítulo adicional largo para probar el scroll y el espaciado de las tarjetas", "2026-08-20 09:15:00"),
]:
    c = Chapter(title=t)
    c.timestamp = ts
    libro.add_chapter(c)

app = ctk.CTk()
app.geometry("900x640")
view = ChapterManagerView(app, libro=libro)
view.pack(fill="both", expand=True)
app.update()
app.update_idletasks()
app.after(300, app.destroy)
app.mainloop()
from PIL import ImageGrab
ImageGrab.grab().save("tmp_shot_view.png")
print("guardado")
