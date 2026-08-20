"""Vista de un Capítulo dentro de un Libro."""

import customtkinter as ctk
from models.chapter import Chapter
from ui.components.inverted_pager import InvertedRawPager
from ui.components.sectors_panel import SectorsPanel
from ui.theme import colors, spacing, radius, sizes, get_font


class ChapterView(ctk.CTkFrame):
    """Vista completa de un capítulo."""

    def __init__(
        self,
        master,
        chapter: Chapter,
        on_toggle_record=None,
        on_full_transcription=None,
        on_export=None,
        on_export_pdf=None,
        on_save=None,
        on_back=None,
    ):
        super().__init__(master, fg_color=colors.bg_primary)
        self.chapter = chapter
        self.on_toggle_record = on_toggle_record
        self.on_full_transcription = on_full_transcription
        self.on_export = on_export
        self.on_export_pdf = on_export_pdf
        self.on_save = on_save
        self.on_back = on_back
        self.is_recording = False

        self._build()

    # ------------------------------------------------------------------
    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_actions_bar()
        self._build_panels()

    # ------------------------------------------------------------------
    def _build_header(self):
        """Cabecera con título y navegación."""
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=spacing.md, pady=(spacing.xs, spacing.sm))

        # Botón volver
        ctk.CTkButton(
            header,
            text="‹ Volver",
            width=sizes.button_small,
            fg_color="transparent",
            hover_color=colors.bg_panel_light,
            text_color=colors.text_primary,
            font=get_font("body"),
            command=self._back,
        ).pack(side="left")

        # Título editable
        self.title_entry = ctk.CTkEntry(
            header,
            font=get_font("heading_medium"),
            text_color=colors.text_primary,
            fg_color=colors.bg_panel_light,
            border_width=1,
            border_color=colors.border,
            width=320,
        )
        self.title_entry.insert(0, self.chapter.title)
        self.title_entry.pack(side="left", padx=spacing.md)

        # Botón guardar (en header)
        ctk.CTkButton(
            header,
            text="💾 Guardar",
            width=sizes.button_medium,
            fg_color=colors.accent,
            hover_color=colors.accent_hover,
            text_color=colors.text_inverse,
            font=get_font("body_small"),
            command=lambda: self.on_save and self.on_save(),
        ).pack(side="right")

    # ------------------------------------------------------------------
    def _build_actions_bar(self):
        """Barra de acciones (grabación y exportación)."""
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=1, column=0, sticky="ew", padx=spacing.md, pady=spacing.sm)

        # Botón grabación
        self.record_btn = ctk.CTkButton(
            actions,
            text="●  Grabar",
            width=sizes.button_large,
            fg_color=colors.danger,
            hover_color=colors.danger_dark,
            text_color=colors.text_inverse,
            font=get_font("body"),
            command=self._toggle_record,
        )
        self.record_btn.pack(side="left", padx=(0, spacing.sm))

        # Medidor VU
        self.vu_bar = ctk.CTkProgressBar(
            actions,
            width=180,
            height=14,
            fg_color=colors.bg_panel_light,
            progress_color=colors.success,
            corner_radius=radius.sm,
        )
        self.vu_bar.set(0.0)
        self.vu_bar.pack(side="left", padx=(spacing.sm, spacing.md))

        # Grupo de acciones
        self._build_action_buttons(actions)

        # Estado
        self.status_label = ctk.CTkLabel(
            actions,
            text="",
            text_color=colors.text_muted,
            font=get_font("body_small"),
        )
        self.status_label.pack(side="right", padx=spacing.md)

    # ------------------------------------------------------------------
    def _build_action_buttons(self, parent):
        """Construye los botones de acción."""
        # Botón transcribir
        ctk.CTkButton(
            parent,
            text="⟳ Transcribir",
            width=sizes.button_large,
            fg_color=colors.accent,
            hover_color=colors.accent_hover,
            text_color=colors.text_inverse,
            font=get_font("body_small"),
            command=lambda: self.on_full_transcription and self.on_full_transcription(),
        ).pack(side="left", padx=spacing.xs)

        # Separador
        self._add_separator(parent)

        # Botón exportar MD
        ctk.CTkButton(
            parent,
            text="📄 .md",
            width=70,
            fg_color=colors.bg_panel_light,
            hover_color=colors.bg_panel,
            text_color=colors.text_primary,
            font=get_font("body_small"),
            command=lambda: self.on_export and self.on_export(),
        ).pack(side="left", padx=spacing.xs)

        # Botón exportar PDF
        ctk.CTkButton(
            parent,
            text="📄 PDF",
            width=70,
            fg_color=colors.bg_panel_light,
            hover_color=colors.bg_panel,
            text_color=colors.text_primary,
            font=get_font("body_small"),
            command=lambda: self.on_export_pdf and self.on_export_pdf(),
        ).pack(side="left", padx=spacing.xs)

    # ------------------------------------------------------------------
    def _add_separator(self, parent):
        """Añade un separador vertical."""
        sep = ctk.CTkFrame(
            parent,
            width=1,
            height=24,
            fg_color=colors.border,
        )
        sep.pack(side="left", padx=spacing.sm)

    # ------------------------------------------------------------------
    def _build_panels(self):
        """Construye los paneles de texto bruto y cuerpo."""
        panels = ctk.CTkFrame(self, fg_color="transparent")
        panels.grid(row=2, column=0, sticky="nsew", padx=spacing.md, pady=(spacing.sm, spacing.sm))

        panels.grid_columnconfigure(0, weight=1, uniform="panel")
        panels.grid_columnconfigure(1, weight=2, uniform="panel")
        panels.grid_rowconfigure(1, weight=1)

        self._build_raw_panel(panels)
        self._build_body_panel(panels)

    # ------------------------------------------------------------------
    def _build_raw_panel(self, parent):
        """Construye el panel de texto bruto."""
        ctk.CTkLabel(
            parent,
            text="📄 Texto bruto",
            font=get_font("heading_small"),
            text_color=colors.text_muted,
        ).grid(row=0, column=0, sticky="w", padx=spacing.xs, pady=(0, spacing.xs))

        char_count = len(self.chapter.raw_text)
        ctk.CTkLabel(
            parent,
            text=f"{char_count:,} caracteres",
            font=get_font("caption"),
            text_color=colors.text_muted,
        ).grid(row=0, column=0, sticky="e", padx=spacing.xs, pady=(0, spacing.xs))

        self.raw_pager = InvertedRawPager(parent, self.chapter.raw_text)
        self.raw_pager.grid(row=1, column=0, sticky="nsew", padx=spacing.xs)

    # ------------------------------------------------------------------
    def _build_body_panel(self, parent):
        """Construye el panel del cuerpo con pestañas."""
        ctk.CTkLabel(
            parent,
            text="📝 Cuerpo del capítulo",
            font=get_font("heading_small"),
            text_color=colors.text_muted,
        ).grid(row=0, column=1, sticky="w", padx=spacing.xs, pady=(0, spacing.xs))

        self.sectors = SectorsPanel(parent, self.chapter)
        self.sectors.grid(row=1, column=1, sticky="nsew", padx=spacing.xs)

    # ------------------------------------------------------------------
    # Métodos públicos
    # ------------------------------------------------------------------
    def append_raw(self, texto_nuevo: str):
        if not texto_nuevo:
            return
        self.raw_pager.append_text(texto_nuevo)

    def sync_after_recording(self):
        self.raw_pager.set_text(self.chapter.raw_text)

    def set_recording_state(self, recording: bool):
        self.is_recording = recording
        if recording:
            self.record_btn.configure(
                text="■  Detener",
                fg_color=colors.warning,
                hover_color="#d35400"
            )
            self.status_label.configure(text="● Grabando…", text_color=colors.danger)
        else:
            self.record_btn.configure(
                text="●  Grabar",
                fg_color=colors.danger,
                hover_color=colors.danger_dark
            )
            self.status_label.configure(text="")
            self.vu_bar.set(0.0)

    def set_volume_level(self, nivel: float):
        nivel = max(0.0, min(1.0, float(nivel)))
        self.vu_bar.set(nivel)

        if nivel > 0.75:
            self.vu_bar.configure(progress_color=colors.danger)
        elif nivel > 0.45:
            self.vu_bar.configure(progress_color=colors.warning)
        else:
            self.vu_bar.configure(progress_color=colors.success)

    def set_status(self, texto: str):
        self.status_label.configure(text=texto)

    def sync_sections(self):
        self.sectors.sync_from_chapter()

    def set_transcribed_text(self, texto: str):
        self.chapter.transcribed_text = texto
        self.sectors.sync_from_chapter()

    def persist_from_ui(self):
        self.chapter.title = self.title_entry.get().strip() or self.chapter.title
        self.sectors.sync_to_chapter()

    def _back(self):
        if self.on_back:
            self.on_back()

    def _toggle_record(self):
        self.is_recording = not self.is_recording
        if self.on_toggle_record:
            self.on_toggle_record(self.is_recording)