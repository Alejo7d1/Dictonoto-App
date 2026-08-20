"""Vista de Biblioteca: lista los libros disponibles.

Permite crear/abrir/eliminar libros y gestionar sus capítulos.
"""
import customtkinter as ctk

from ui.theme import colors


class LibraryView(ctk.CTkFrame):
    """Panel inicial con la lista de libros y capítulos."""

    def __init__(
        self,
        master,
        libros,
        on_new_book=None,          # callable()
        on_edit_book=None,         # callable(libro)
        on_delete_book=None,       # callable(libro)
        on_open_book=None,         # callable(libro)
    ):
        super().__init__(master, fg_color="#121212")
        self.libros = libros or []
        self.on_new_book = on_new_book
        self.on_edit_book = on_edit_book
        self.on_delete_book = on_delete_book
        self.on_open_book = on_open_book

        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Scroll de libros
        scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
        )
        scroll.grid(row=0, column=0, sticky="nsew", padx=20, pady=16)
        scroll.grid_columnconfigure(0, weight=1)

        # Encabezado
        ctk.CTkLabel(
            scroll, text="Mi Biblioteca",
            font=ctk.CTkFont(size=24, weight="bold"), text_color=colors.text_primary,
        ).grid(row=0, column=0, sticky="w", pady=(0, 4))

        ctk.CTkLabel(
            scroll, text="Selecciona o crea un libro para empezar a transcribir",
            font=ctk.CTkFont(size=13), text_color=colors.text_secondary,
        ).grid(row=1, column=0, sticky="w", pady=(0, 12))

        ctk.CTkButton(
            scroll, text="＋  Nuevo Libro", width=160,
            fg_color=colors.accent, hover_color=colors.accent_hover, text_color="white",
            command=lambda: self.on_new_book and self.on_new_book(),
        ).grid(row=2, column=0, sticky="w", pady=(0, 14))

        self.cards_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        self.cards_frame.grid(row=3, column=0, sticky="ew")
        self.cards_frame.grid_columnconfigure(0, weight=1)

        self._render_card_list()

    def _render_card_list(self):
        # Limpiar tarjetas previas
        for widget in self.cards_frame.winfo_children():
            widget.destroy()

        if not self.libros:
            ctk.CTkLabel(
                self.cards_frame,
                text="Aún no hay libros. Crea el primero con 「＋ Nuevo Libro」.",
                text_color=colors.text_secondary, font=ctk.CTkFont(size=14),
            ).grid(row=0, column=0, sticky="w", pady=20)
            return

        for i, libro in enumerate(self.libros):
            card = ctk.CTkFrame(
                self.cards_frame, fg_color=colors.bg_panel,
                corner_radius=12, border_width=1, border_color=colors.border,
            )
            card.grid(row=i, column=0, sticky="ew", pady=6)
            card.grid_columnconfigure(1, weight=1)

            # Indicador de color
            ctk.CTkLabel(
                card, text="   ", width=12, fg_color=libro.color_hex,
                corner_radius=6, text_color=colors.bg_panel,
            ).grid(row=0, column=0, rowspan=2, padx=12, pady=12)

            # Nombre y descripción
            ctk.CTkLabel(
                card, text=libro.name,
                font=ctk.CTkFont(size=16, weight="bold"), text_color=colors.text_primary,
            ).grid(row=0, column=1, sticky="w", padx=6, pady=(10, 0))

            ctk.CTkLabel(
                card, text=libro.description or "Sin descripción",
                font=ctk.CTkFont(size=12), text_color=colors.text_secondary,
                anchor="w",
            ).grid(row=1, column=1, sticky="w", padx=6, pady=(0, 10))

            # Acciones
            acciones = ctk.CTkFrame(card, fg_color="transparent")
            acciones.grid(row=0, column=2, rowspan=2, padx=10)

            ctk.CTkButton(
                acciones, text=f"{len(libro.chapters)} cap.  ›",
                width=110, fg_color=colors.accent, hover_color=colors.accent_hover,
                text_color="white",
                command=lambda l=libro: self.on_open_book and self.on_open_book(l),
            ).pack(side="left", padx=4)

            ctk.CTkButton(
                acciones, text="✎", width=36,
                fg_color=colors.bg_panel_light, hover_color="#3a3a3a", text_color=colors.text_primary,
                command=lambda l=libro: self.on_edit_book and self.on_edit_book(l),
            ).pack(side="left", padx=2)

            ctk.CTkButton(
                acciones, text="🗑", width=36,
                fg_color="transparent", hover_color="#4a2020",
                text_color="#e74c3c",
                command=lambda l=libro: self.on_delete_book and self.on_delete_book(l),
            ).pack(side="left", padx=2)
