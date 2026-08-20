"""Hoja de texto bruto con paginación invertida para documentos largos."""

import customtkinter as ctk
from ui.theme import colors, typography, spacing, radius

PAGE_SIZE = 2500
PAGE_CARGADAS_INICIAL = 2
UMBRAL_TOPE = 0.05


def _dividir_en_paginas(texto: str, tam: int = PAGE_SIZE) -> list:
    """Divide un texto continuo en páginas sin cortar palabras."""
    if not texto:
        return []

    paginas = []
    inicio = 0
    n = len(texto)

    while inicio < n:
        fin = min(inicio + tam, n)

        if fin < n:
            corte = texto.rfind(" ", inicio, fin)
            if corte > inicio:
                fin = corte

        paginas.append(texto[inicio:fin].strip())
        inicio = fin

        while inicio < n and texto[inicio] == " ":
            inicio += 1

    return [p for p in paginas if p]


class InvertedRawPager(ctk.CTkFrame):
    """Recipiente de la hoja de texto bruto con paginación invertida."""

    def __init__(self, master, texto_inicial="", **kwargs):
        super().__init__(master, fg_color=colors.bg_panel, **kwargs)
        self.texto_completo = texto_inicial or ""
        self._paginas: list = []
        self._idx_inicio: int = 0

        self._build()
        self.set_text(self.texto_completo)

    # ------------------------------------------------------------------
    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Contenedor con borde
        container = ctk.CTkFrame(
            self,
            fg_color=colors.bg_panel,
            border_width=1,
            border_color=colors.border,
            corner_radius=radius.md,
        )
        container.grid(row=0, column=0, sticky="nsew")
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

        # Textbox
        self.textbox = ctk.CTkTextbox(
            container,
            fg_color=colors.bg_panel,
            text_color=colors.text_primary,
            border_width=0,
            font=typography.body,
            wrap="word",
            state="disabled",
        )
        self.textbox.grid(row=0, column=0, sticky="nsew", padx=spacing.xs, pady=spacing.xs)

        # Eventos para paginación
        self._bind_scroll_events()

    # ------------------------------------------------------------------
    def _bind_scroll_events(self):
        """Vincula eventos de scroll para cargar páginas anteriores."""
        self.textbox.bind("<MouseWheel>", self._on_wheel)
        self.textbox.bind("<Button-4>", self._on_wheel)
        self.textbox.bind("<Button-5>", self._on_wheel)
        self.textbox.bind("<KeyPress-Up>", self._on_key_top)
        self.textbox.bind("<KeyPress-Prior>", self._on_key_top)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def set_text(self, texto: str):
        """Carga un texto completo desde cero."""
        self.texto_completo = texto or ""
        self._paginas = _dividir_en_paginas(self.texto_completo)

        primera = max(0, len(self._paginas) - PAGE_CARGADAS_INICIAL)
        self._render(primera)
        self._ir_al_final()

    def append_text(self, texto_nuevo: str):
        """Añade texto nuevo al final."""
        if not texto_nuevo:
            return

        self.texto_completo += texto_nuevo
        en_final = self._esta_en_final()

        self._paginas = _dividir_en_paginas(self.texto_completo)
        primera = max(0, len(self._paginas) - PAGE_CARGADAS_INICIAL)
        self._render(primera)

        if en_final:
            self._ir_al_final()

    # ------------------------------------------------------------------
    def _esta_en_final(self) -> bool:
        try:
            y0, _ = self.textbox.yview()
            return y0 >= 1.0 - UMBRAL_TOPE
        except Exception:
            return True

    # ------------------------------------------------------------------
    def _render(self, idx_inicio: int):
        """Reemplaza el widget con las páginas desde idx_inicio."""
        self._idx_inicio = max(0, min(idx_inicio, len(self._paginas) - 1)) if self._paginas else 0

        contenido = "\n".join(self._paginas[self._idx_inicio:])

        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")

        if contenido:
            self.textbox.insert("1.0", contenido + "\n")

        self.textbox.configure(state="disabled")

    def _ir_al_final(self):
        try:
            self.textbox.see("end")
        except Exception:
            pass

    # ------------------------------------------------------------------
    def _cargar_mas_arriba(self):
        """Carga una página más arriba."""
        if self._idx_inicio <= 0:
            return

        nueva = self._idx_inicio - 1
        bloque = self._paginas[nueva] + "\n"

        ancla = self.textbox.index("@0,0")
        self.textbox.configure(state="normal")
        self.textbox.insert("1.0", bloque)
        self.textbox.configure(state="disabled")

        self._idx_inicio = nueva
        self.textbox.see(ancla)

    # ------------------------------------------------------------------
    def _on_wheel(self, event):
        """Detecta scroll hacia arriba."""
        if self._idx_inicio <= 0:
            return

        hacia_arriba = event.num in (4,) or (hasattr(event, "delta") and event.delta > 0)
        if hacia_arriba:
            try:
                y0, _ = self.textbox.yview()
                if y0 <= UMBRAL_TOPE:
                    self._cargar_mas_arriba()
            except Exception:
                pass

    def _on_key_top(self, _event):
        """Carga más páginas con teclado."""
        if self._idx_inicio <= 0:
            return

        try:
            y0, _ = self.textbox.yview()
            if y0 <= UMBRAL_TOPE:
                self._cargar_mas_arriba()
        except Exception:
            pass