"""Vista de un Capítulo dentro de un Libro.

Muestra:
- Cabecera con el título del capítulo.
- Dos hojas una a la par de la otra:
    - Hoja 1: texto bruto (sin limpiar), de solo lectura.
    - Hoja 2: el "cuerpo", que se muestra como subventanas (pestañas):
      Resumen, Datos importantes, Glosario y Cuerpo.
- Controles del grabador (iniciar/detener, transcripción completa),
  exportación a Markdown y guardado.
"""
import customtkinter as ctk

from models.chapter import Chapter
from ui.components.inverted_pager import InvertedRawPager
from ui.components.sectors_panel import SectorsPanel, TEXTO, SUBTEXTO, PANEL, PANEL2

ACCENTO = "#6c5ce7"


class ChapterView(ctk.CTkFrame):
    """Vista completa de un capítulo."""

    def __init__(
        self,
        master,
        chapter: Chapter,
        on_toggle_record=None,   # callable(recording: bool)
        on_full_transcription=None,  # callable()
        on_export=None,          # callable() - exportar a Markdown
        on_export_pdf=None,      # callable() - exportar a PDF
        on_save=None,            # callable()
        on_back=None,            # callable()
    ):
        super().__init__(master, fg_color="#121212")
        self.chapter = chapter
        self.on_toggle_record = on_toggle_record
        self.on_full_transcription = on_full_transcription
        self.on_export = on_export
        self.on_export_pdf = on_export_pdf
        self.on_save = on_save
        self.on_back = on_back
        self.is_recording = False
        # Longitud del texto bruto ya mostrado en el widget. Permite
        # insertar solo el fragmento nuevo (en tiempo real) en lugar de
        # reconstruir todo el texto en cada refresco (evita lentitud
        # progresiva con más contenido).
        self._raw_shown_len = 0

        self._build()

    # ------------------------------------------------------------------
    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # --- Cabecera ---
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 4))

        ctk.CTkButton(
            header, text="‹ Volver", width=80,
            fg_color="transparent", hover_color=PANEL2,
            text_color=TEXTO, command=self._back,
        ).pack(side="left")

        self.title_entry = ctk.CTkEntry(
            header,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=TEXTO,
            fg_color=PANEL2, border_width=1, border_color=PANEL2,
            width=320,
        )
        self.title_entry.insert(0, self.chapter.title)
        self.title_entry.pack(side="left", padx=12)

        # --- Barra de acciones (grabar y transcripción completa) ---
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=1, column=0, sticky="ew", padx=14, pady=4)

        self.record_btn = ctk.CTkButton(
            actions, text="●  Grabar", width=130,
            fg_color="#e74c3c", hover_color="#c0392b",
            text_color="white", font=ctk.CTkFont(size=14, weight="bold"),
            command=self._toggle_record,
        )
        self.record_btn.pack(side="left", padx=(0, 8))

        # Medidor de nivel de audio en vivo (VU meter)
        self.vu_bar = ctk.CTkProgressBar(
            actions, width=180, height=14,
            fg_color=PANEL2, progress_color="#2ecc71",
            corner_radius=4,
        )
        self.vu_bar.set(0.0)
        self.vu_bar.pack(side="left", padx=(4, 8))

        self.full_btn = ctk.CTkButton(
            actions, text="⟳  Transcribir", width=200,
            fg_color=ACCENTO, hover_color="#5a4bd1",
            text_color="white", font=ctk.CTkFont(size=13),
            command=lambda: self.on_full_transcription and self.on_full_transcription(),
        )
        self.full_btn.pack(side="left", padx=8)

        ctk.CTkButton(
            actions, text="⤓ Exportar a .md", width=110,
            fg_color=PANEL2, hover_color="#3a3a3a",
            text_color=TEXTO, font=ctk.CTkFont(size=13),
            command=lambda: self.on_export and self.on_export(),
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            actions, text="⤓ Exportar a PDF", width=110,
            fg_color=PANEL2, hover_color="#3a3a3a",
            text_color=TEXTO, font=ctk.CTkFont(size=13),
            command=lambda: self.on_export_pdf and self.on_export_pdf(),
        ).pack(side="left", padx=8)

        self.status_label = ctk.CTkLabel(
            actions, text="", text_color=SUBTEXTO, font=ctk.CTkFont(size=12),
        )
        self.status_label.pack(side="right")

        ctk.CTkButton(
            actions, text="Guardar", width=90,
            fg_color=PANEL2, hover_color="#3a3a3a",
            text_color=TEXTO, command=lambda: self.on_save and self.on_save(),
        ).pack(side="right", padx=8)

        # --- Dos hojas: bruta (estrecha) + transcrita (grande) ---
        hojas = ctk.CTkFrame(self, fg_color="transparent")
        hojas.grid(row=2, column=0, sticky="nsew", padx=14, pady=(4, 8))
        # Proporción: 1/3 bruto, 2/3 transcrito (el bloque principal)
        hojas.grid_columnconfigure(0, weight=1, uniform="hoja")
        hojas.grid_columnconfigure(1, weight=2, uniform="hoja")
        hojas.grid_rowconfigure(1, weight=1)

        # Hoja 1: texto bruto (columna izquierda, más estrecha)
        ctk.CTkLabel(
            hojas, text="Texto bruto (sin limpiar)",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=SUBTEXTO,
        ).grid(row=0, column=0, sticky="w", padx=4, pady=(0, 4))

        # Hoja 1 usa paginación invertida: solo se cargan las últimas
        # páginas y se va cargando hacia arriba al llegar al tope, además
        # de sin ajuste de línea (wrap="none") para que el scroll sea
        # rápido incluso con documentos de miles de palabras.
        self.raw_pager = InvertedRawPager(hojas, self.chapter.raw_text)
        self.raw_pager.grid(row=1, column=0, sticky="nsew", padx=4)

        # Hoja 2: el cuerpo, mostrado como subventanas (pestañas) de sectores
        ctk.CTkLabel(
            hojas, text="Cuerpo (Resumen · Datos · Glosario · Cuerpo)",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=SUBTEXTO,
        ).grid(row=0, column=1, sticky="w", padx=4, pady=(0, 4))

        self.sectors = SectorsPanel(hojas, self.chapter)
        self.sectors.grid(row=1, column=1, sticky="nsew", padx=4)

    # ------------------------------------------------------------------
    def _back(self):
        if self.on_back:
            self.on_back()

    def _toggle_record(self):
        self.is_recording = not self.is_recording
        if self.on_toggle_record:
            self.on_toggle_record(self.is_recording)

    # ------------------------------------------------------------------
    # Actualización de la UI
    # ------------------------------------------------------------------
    def append_raw(self, texto_nuevo: str):
        """Añade texto nuevo al final de la hoja bruta (inserción incremental).

        Usa el pager de paginación invertida, que solo recalcula las
        últimas páginas visibles y se mantiene pegado al final. Esto
        mantiene la UI fluida aunque se acumulen muchas transcripciones.
        """
        if not texto_nuevo:
            return
        self.raw_pager.append_text(texto_nuevo)

    def sync_after_recording(self):
        """Refresca la hoja de texto bruto (recarga desde el capítulo).

        Se usa cuando el texto pudo cambiar "por fuera" (p. ej. al abrir
        un capítulo guardado). Para la transcripción en vivo se prefiere
        `append_raw`, que es mucho más barata.
        """
        self.raw_pager.set_text(self.chapter.raw_text)

    def set_recording_state(self, recording: bool):
        self.is_recording = recording
        if recording:
            self.record_btn.configure(
                text="■  Detener", fg_color="#e67e22", hover_color="#d35400"
            )
            self.status_label.configure(
                text="● Grabando…", text_color="#e74c3c"
            )
        else:
            self.record_btn.configure(
                text="●  Grabar", fg_color="#e74c3c", hover_color="#c0392b"
            )
            self.status_label.configure(text="")
            self.vu_bar.set(0.0)

    def set_volume_level(self, nivel: float):
        """Actualiza el medidor de sonido en vivo (0.0 - 1.0)."""
        nivel = max(0.0, min(1.0, float(nivel)))
        self.vu_bar.set(nivel)
        # Cambia el color según intensidad: verde (bajo), naranja (medio),
        # rojo (alto).
        if nivel > 0.75:
            self.vu_bar.configure(progress_color="#e74c3c")
        elif nivel > 0.45:
            self.vu_bar.configure(progress_color="#f39c12")
        else:
            self.vu_bar.configure(progress_color="#2ecc71")

    def set_status(self, texto: str):
        self.status_label.configure(text=texto)

    def sync_sections(self):
        """Recarga los sectores (tras la transcripción completa)."""
        self.sectors.sync_from_chapter()

    def set_transcribed_text(self, texto: str):
        """Actualiza el texto transcrito (cuerpo) en el capítulo y la UI."""
        self.chapter.transcribed_text = texto
        self.sectors.sync_from_chapter()

    def persist_from_ui(self):
        """Guarda los campos editables hacia el capítulo."""
        self.chapter.title = self.title_entry.get().strip() or self.chapter.title
        self.sectors.sync_to_chapter()
