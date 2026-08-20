"""Vista de gestión de capítulos dentro de un libro."""

import customtkinter as ctk
from models.book import Book
from models.chapter import Chapter
from ui.theme import colors, typography, spacing, radius, sizes


class ChapterManagerView(ctk.CTkFrame):
    """Página para gestionar los capítulos de un libro."""

    def __init__(
        self,
        master,
        libro: Book,
        on_open_chapter=None,
        on_back=None,
        on_delete=None,
    ):
        super().__init__(master, fg_color=colors.bg_primary)
        self.libro = libro
        self.on_open_chapter = on_open_chapter
        self.on_back = on_back
        self.on_delete = on_delete

        self._build()

    # ------------------------------------------------------------------
    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_chapter_list()
        self._build_footer()
        self._render_list()

    # ------------------------------------------------------------------
    def _build_header(self):
        """Cabecera con título y botón de nuevo capítulo."""
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=spacing.md, pady=(spacing.xs, spacing.sm))
        header.grid_columnconfigure(1, weight=1)

        # Botón volver
        ctk.CTkButton(
            header,
            text="‹ Volver",
            width=sizes.button_small,
            fg_color="transparent",
            hover_color=colors.bg_panel_light,
            text_color=colors.text_primary,
            command=self._back,
            font=typography.body,
        ).grid(row=0, column=0, sticky="w")

        # Título
        ctk.CTkLabel(
            header,
            text=f"Capítulos de «{self.libro.name}»",
            font=typography.heading_medium,
            text_color=colors.text_primary,
        ).grid(row=0, column=1, padx=spacing.md)

        # Botón nuevo capítulo
        ctk.CTkButton(
            header,
            text="＋ Nuevo Capítulo",
            fg_color=colors.accent,
            hover_color=colors.accent_hover,
            text_color=colors.text_inverse,
            width=sizes.button_large,
            font=typography.body,
            command=self._crear_nuevo,
        ).grid(row=0, column=2, sticky="e")

    # ------------------------------------------------------------------
    def _build_chapter_list(self):
        """Lista scrollable de capítulos."""
        self.list_frame = ctk.CTkScrollableFrame(
            self,
            fg_color=colors.bg_panel,
            corner_radius=radius.lg,
        )
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=spacing.lg, pady=spacing.md)
        self.list_frame.grid_columnconfigure(0, weight=1)

    # ------------------------------------------------------------------
    def _build_footer(self):
        """Pie de página."""
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=spacing.lg, pady=(0, spacing.xs))

        ctk.CTkButton(
            footer,
            text="‹ Volver a la biblioteca",
            width=sizes.button_large,
            fg_color="transparent",
            hover_color=colors.bg_panel_light,
            text_color=colors.text_muted,
            font=typography.body,
            command=self._back,
        ).pack(side="left")

        # Contador de capítulos
        ctk.CTkLabel(
            footer,
            text=f"{len(self.libro.chapters)} capítulos",
            text_color=colors.text_muted,
            font=typography.caption,
        ).pack(side="right")

    # ------------------------------------------------------------------
    def _crear_nuevo(self):
        """Crea un nuevo capítulo y lo abre."""
        nuevo = Chapter(title="Nuevo Capítulo")
        self.libro.add_chapter(nuevo)
        self._render_list()

        if self.on_open_chapter:
            self.on_open_chapter(nuevo)

    # ------------------------------------------------------------------
    def _render_list(self):
        """Renderiza la lista de capítulos."""
        # Limpiar
        for w in self.list_frame.winfo_children():
            w.destroy()

        # Mensaje vacío
        if not self.libro.chapters:
            self._render_empty_state()
            return

        # Renderizar cada capítulo
        for i, ch in enumerate(self.libro.chapters):
            self._render_chapter_row(i, ch)

    # ------------------------------------------------------------------
    def _render_empty_state(self):
        """Muestra mensaje cuando no hay capítulos."""
        ctk.CTkLabel(
            self.list_frame,
            text="📖  Sin capítulos todavía. ¡Crea uno nuevo!",
            text_color=colors.text_muted,
            font=typography.body_large,
        ).grid(row=0, column=0, pady=spacing.xl)

    # ------------------------------------------------------------------
    def _render_chapter_row(self, index: int, chapter: Chapter):
        """Renderiza una fila de capítulo."""
        row = ctk.CTkFrame(
            self.list_frame,
            fg_color=colors.bg_card,
            corner_radius=radius.md,
            border_width=1,
            border_color=colors.bg_panel_light,
        )
        row.grid(row=index, column=0, sticky="ew", pady=spacing.sm, padx=spacing.xs)
        row.grid_columnconfigure(1, weight=1)

        # Número de capítulo (badge)
        ctk.CTkLabel(
            row,
            text=f"{index + 1}",
            width=34,
            height=34,
            corner_radius=17,
            fg_color=colors.accent,
            text_color=colors.text_inverse,
            font=typography.heading_small,
        ).grid(row=0, column=0, rowspan=2, padx=(spacing.md, spacing.sm), pady=spacing.md)

        # Título
        ctk.CTkLabel(
            row,
            text=chapter.title,
            font=typography.heading_small,
            text_color=colors.text_primary,
            anchor="w",
        ).grid(row=0, column=1, sticky="ew", padx=(0, spacing.sm), pady=(spacing.md, 0))

        # Timestamp
        ctk.CTkLabel(
            row,
            text=f"🕒 {chapter.timestamp}",
            font=typography.caption,
            text_color=colors.text_muted,
            anchor="w",
        ).grid(row=1, column=1, sticky="ew", padx=(0, spacing.sm), pady=(0, spacing.md))

        # Botones de acción
        self._render_row_buttons(row, chapter)

    # ------------------------------------------------------------------
    def _render_row_buttons(self, row: ctk.CTkFrame, chapter: Chapter):
        """Renderiza los botones de acción de una fila."""
        # Botón Abrir
        ctk.CTkButton(
            row,
            text="Abrir",
            width=sizes.button_small,
            fg_color=colors.accent,
            hover_color=colors.accent_hover,
            text_color=colors.text_inverse,
            font=typography.body_small,
            command=lambda c=chapter: self._abrir(c),
        ).grid(row=0, column=2, rowspan=2, padx=spacing.sm, pady=spacing.md)

        # Botón Eliminar
        ctk.CTkButton(
            row,
            text="🗑",
            width=40,
            fg_color="transparent",
            hover_color="#3a1a1a",
            text_color=colors.danger,
            font=typography.body,
            command=lambda c=chapter: self._eliminar(c),
        ).grid(row=0, column=3, rowspan=2, padx=(0, spacing.md), pady=spacing.md)

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