"""Vista de gestión de capítulos dentro de un libro (página inline).

Se muestra como página dentro de la ventana principal, no como ventana
modal. Permite crear, abrir y eliminar capítulos.
"""
import customtkinter as ctk

from models.book import Book
from models.chapter import Chapter

BG = "#121212"
PANEL = "#1e1e1e"
PANEL2 = "#2a2a2a"
ACCENTO = "#6c5ce7"
TEXTO = "#e8e8e8"
SUBTEXTO = "#9a9a9a"


class ChapterManagerView(ctk.CTkFrame):
    """Página para gestionar los capítulos de un libro."""

    def __init__(
        self,
        master,
        libro: Book,
        on_open_chapter=None,  # callable(chapter)
        on_back=None,          # callable()
        on_delete=None,        # callable(libro) -> para confirmar/borrar libro
    ):
        super().__init__(master, fg_color=BG)
        self.libro = libro
        self.on_open_chapter = on_open_chapter
        self.on_back = on_back
        self.on_delete = on_delete

        self._build()

    # ------------------------------------------------------------------
    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Cabecera
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 4))
        header.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            header, text="‹ Volver", width=80,
            fg_color="transparent", hover_color=PANEL2,
            text_color=TEXTO, command=self._back,
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header, text=f"Capítulos de «{self.libro.name}»",
            font=ctk.CTkFont(size=18, weight="bold"), text_color=TEXTO,
        ).grid(row=0, column=1, padx=8)

        ctk.CTkButton(
            header, text="＋  Nuevo Capítulo", fg_color=ACCENTO,
            hover_color="#5a4bd1", text_color="white", width=160,
            command=self._crear_nuevo,
        ).grid(row=0, column=2, sticky="e")

        # Lista de capítulos
        self.list_frame = ctk.CTkScrollableFrame(
            self, fg_color=PANEL, corner_radius=10,
        )
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=8)
        self.list_frame.grid_columnconfigure(0, weight=1)

        # Fila inferior (volver a biblioteca)
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 10))
        ctk.CTkButton(
            footer, text="‹ Volver a la biblioteca", width=160,
            fg_color="transparent", hover_color=PANEL2,
            text_color=SUBTEXTO, command=self._back,
        ).pack(side="left")

        self._render_list()

    # ------------------------------------------------------------------
    def _crear_nuevo(self):
        """Añade un nuevo capítulo con título por defecto (título editable)."""
        nuevo = Chapter(title="Nuevo Capítulo")
        self.libro.add_chapter(nuevo)
        self._render_list()
        # Abre directamente para permitir guardar/editar
        if self.on_open_chapter:
            self.on_open_chapter(nuevo)

    def _render_list(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

        if not self.libro.chapters:
            ctk.CTkLabel(
                self.list_frame, text="Sin capítulos todavía. Crea uno nuevo.",
                text_color=SUBTEXTO,
            ).grid(row=0, column=0, pady=20)
            return

        for i, ch in enumerate(self.libro.chapters):
            row = ctk.CTkFrame(self.list_frame, fg_color=PANEL2, corner_radius=8)
            row.grid(row=i, column=0, sticky="ew", pady=4, padx=4)
            row.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                row, text=ch.title,
                font=ctk.CTkFont(size=14, weight="bold"), text_color=TEXTO,
            ).grid(row=0, column=0, sticky="w", padx=12, pady=6)

            ctk.CTkLabel(
                row, text=ch.timestamp,
                font=ctk.CTkFont(size=11), text_color=SUBTEXTO,
            ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 8))

            ctk.CTkButton(
                row, text="Abrir", width=80,
                fg_color=ACCENTO, hover_color="#5a4bd1", text_color="white",
                command=lambda c=ch: self._abrir(c),
            ).grid(row=0, column=1, rowspan=2, padx=6)

            ctk.CTkButton(
                row, text="🗑", width=40,
                fg_color="transparent", hover_color="#4a2020",
                text_color="#e74c3c",
                command=lambda c=ch: self._eliminar(c),
            ).grid(row=0, column=2, rowspan=2, padx=6)

    # ------------------------------------------------------------------
    def _back(self):
        if self.on_back:
            self.on_back()

    def _abrir(self, cap):
        if self.on_open_chapter:
            self.on_open_chapter(cap)

    def _eliminar(self, cap):
        self.libro.chapters.remove(cap)
        self._render_list()
