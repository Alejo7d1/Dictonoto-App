"""Vista para crear o editar un Libro (página inline, no diálogo).

Se muestra dentro de la ventana principal en lugar de una ventana modal.
Los diálogos modales quedan reservados únicamente para alertas.
"""
import customtkinter as ctk

from models.book import Book

BG = "#121212"
PANEL = "#1e1e1e"
PANEL2 = "#2a2a2a"
ACCENTO = "#6c5ce7"
TEXTO = "#e8e8e8"
SUBTEXTO = "#9a9a9a"

COLORES = [
    "#6c5ce7", "#3B82F6", "#10b981", "#f59e0b",
    "#ef4444", "#ec4899", "#14b8a6", "#8b5cf6",
]


class BookView(ctk.CTkFrame):
    """Página para crear o editar un libro."""

    def __init__(
        self,
        master,
        libro: Book | None = None,
        on_saved=None,     # callable(libro)
        on_back=None,      # callable()
        on_delete=None,    # callable(libro)  -- opcional
    ):
        super().__init__(master, fg_color=BG)
        self.libro = libro  # None => crear nuevo
        self.on_saved = on_saved
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

        ctk.CTkButton(
            header, text="‹ Volver", width=80,
            fg_color="transparent", hover_color=PANEL2,
            text_color=TEXTO, command=self._back,
        ).pack(side="left")

        titulo = "Nuevo Libro" if self.libro is None else "Editar Libro"
        ctk.CTkLabel(
            header, text=titulo,
            font=ctk.CTkFont(size=20, weight="bold"), text_color=TEXTO,
        ).pack(side="left", padx=12)

        # Cuerpo
        body = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=12)
        body.grid(row=1, column=0, sticky="nsew", padx=40, pady=16)
        body.grid_columnconfigure(0, weight=1)

        # Nombre
        ctk.CTkLabel(
            body, text="Nombre",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXTO, anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=24, pady=(18, 4))
        self.name_entry = ctk.CTkEntry(
            body, fg_color=PANEL2, text_color=TEXTO,
            border_width=1, border_color=PANEL,
        )
        if self.libro:
            self.name_entry.insert(0, self.libro.name)
        self.name_entry.grid(row=1, column=0, sticky="ew", padx=24)

        # Color
        ctk.CTkLabel(
            body, text="Color",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXTO, anchor="w",
        ).grid(row=2, column=0, sticky="w", padx=24, pady=(16, 4))

        color_frame = ctk.CTkFrame(body, fg_color="transparent")
        color_frame.grid(row=3, column=0, sticky="w", padx=24)
        self._color_var = ctk.StringVar(
            value=self.libro.color_hex if self.libro else COLORES[0]
        )
        self._color_buttons = []
        for hexa in COLORES:
            btn = ctk.CTkButton(
                color_frame,
                text="", width=34, height=34, corner_radius=34,
                fg_color=hexa,
                border_width=2,
                border_color="#ffffff" if self._color_var.get() == hexa else PANEL2,
                command=lambda c=hexa: self._seleccionar_color(c),
            )
            btn.pack(side="left", padx=5, pady=4)
            self._color_buttons.append(btn)

        # Descripción
        ctk.CTkLabel(
            body, text="Descripción",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXTO, anchor="w",
        ).grid(row=4, column=0, sticky="w", padx=24, pady=(16, 4))
        self.desc_box = ctk.CTkTextbox(
            body, height=90, fg_color=PANEL2, text_color=TEXTO,
            border_width=1, border_color=PANEL,
            font=ctk.CTkFont(size=12),
        )
        if self.libro:
            self.desc_box.insert("1.0", self.libro.description)
        self.desc_box.grid(row=5, column=0, sticky="ew", padx=24, pady=(0, 18))

        # Botones
        botones = ctk.CTkFrame(body, fg_color="transparent")
        botones.grid(row=6, column=0, sticky="w", padx=24, pady=(0, 18))
        ctk.CTkButton(
            botones, text="Guardar", width=140,
            fg_color=ACCENTO, hover_color="#5a4bd1", text_color="white",
            command=self._guardar,
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            botones, text="Cancelar", width=100,
            fg_color="transparent", hover_color=PANEL2, text_color=SUBTEXTO,
            command=self._back,
        ).pack(side="left", padx=6)
        if self.libro:
            ctk.CTkButton(
                botones, text="Eliminar", width=100,
                fg_color="transparent", hover_color="#4a2020", text_color="#e74c3c",
                command=self._eliminar,
            ).pack(side="left", padx=6)

    # ------------------------------------------------------------------
    def _seleccionar_color(self, hexa):
        self._color_var.set(hexa)
        for btn in self._color_buttons:
            btn.configure(
                border_color="#ffffff"
                if self._color_var.get() == btn.cget("fg_color")
                else PANEL2
            )

    def _back(self):
        if self.on_back:
            self.on_back()

    def _guardar(self):
        nombre = self.name_entry.get().strip()
        if not nombre:
            return
        color = self._color_var.get()
        desc = self.desc_box.get("1.0", "end").strip()

        if self.libro is None:
            self.libro = Book(name=nombre, description=desc, color_hex=color)
        else:
            self.libro.name = nombre
            self.libro.description = desc
            self.libro.color_hex = color

        if self.on_saved:
            self.on_saved(self.libro)

    def _eliminar(self):
        if self.on_delete and self.libro:
            self.on_delete(self.libro)
        elif self.on_back:
            self.on_back()
