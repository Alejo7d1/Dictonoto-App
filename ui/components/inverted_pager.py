"""Hoja de texto bruto con rendimiento para documentos largos.

El widget ``Text`` de Tk/Tkinter se degrada mucho con documentos grandes
si se inserta TODO el texto a la vez (decenas de miles de líneas con reflow)
y si el ajuste de línea (``wrap="word"``) está activo en una columna
estrecha: cargar y desplazarse se vuelve muy lento.

Este componente resuelve el problema con **paginación invertida**:
al abrir un capítulo solo se cargan las últimas páginas (las más
recientes), de modo que la carga inicial es instantánea. Al hacer scroll
arriba del todo se cargan progresivamente las páginas más antiguas, como
una conversación de red social (chat). Nuevas transcripciones se añaden
al final sin recargar nada.

El ajuste de línea se mantiene normal (``wrap="word"``) para que el
texto sea legible.
"""

import customtkinter as ctk

PANEL = "#1e1e1e"
PANEL2 = "#2a2a2a"
TEXTO = "#e8e8e8"

# Caracteres por página. Cada página se muestra como una línea en el widget.
PAGE_SIZE = 2500
# Cuántas páginas (las más recientes) se muestran al abrir.
PAGE_CARGADAS_INICIAL = 2
# Umbral (fracción del top) para considerar que el usuario "llegó arriba".
UMBRAL_TOPE = 0.05


def _dividir_en_paginas(texto: str, tam: int = PAGE_SIZE) -> list:
    """Divide un texto continuo en páginas sin cortar palabras.

    Corta cerca de ``tam`` caracteres, retrocediendo hasta el último
    espacio para no partir una palabra a la mitad. Devuelve una lista de
    cadenas (sin salto de línea final).
    """
    if not texto:
        return []
    paginas = []
    inicio = 0
    n = len(texto)
    while inicio < n:
        fin = min(inicio + tam, n)
        if fin < n:
            # Retrocede hasta un espacio para no cortar palabras.
            corte = texto.rfind(" ", inicio, fin)
            if corte > inicio:  # solo retrocedemos si hay un espacio útil
                fin = corte
        paginas.append(texto[inicio:fin].strip())
        inicio = fin
        # Salta el espacio de separación sobrante para no empezar con espacio.
        while inicio < n and texto[inicio] == " ":
            inicio += 1
    # Descarta páginas vacías.
    return [p for p in paginas if p]


class InvertedRawPager(ctk.CTkFrame):
    """Recipiente de la hoja de texto bruto con paginación invertida.

    Mantiene el texto completo en ``self.texto_completo`` (fuente de
    verdad) y solo renderiza en el widget las páginas cargadas.
    """

    def __init__(self, master, texto_inicial="", **kwargs):
        super().__init__(master, fg_color=PANEL, **kwargs)
        self.texto_completo = texto_inicial or ""
        self._paginas: list = []          # todas las páginas (de antigua a nueva)
        self._idx_inicio: int = 0         # primera página renderizada (índice en _paginas)

        self._build()
        self.set_text(self.texto_completo)

    # ------------------------------------------------------------------
    # Construcción de la UI
    # ------------------------------------------------------------------
    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.textbox = ctk.CTkTextbox(
            self,
            fg_color=PANEL, text_color=TEXTO,
            border_width=1, border_color=PANEL2,
            font=ctk.CTkFont(size=13),
            wrap="word",           # ajuste de línea normal (legible)
            state="disabled",
        )
        self.textbox.grid(row=0, column=0, sticky="nsew")

        # Detección de "llegar al tope" para cargar páginas anteriores.
        self.textbox.bind("<MouseWheel>", self._on_wheel)
        # Para Linux (botón 4/5). En Windows basta <MouseWheel>.
        self.textbox.bind("<Button-4>", self._on_wheel)
        self.textbox.bind("<Button-5>", self._on_wheel)
        self.textbox.bind("<KeyPress-Up>", self._on_key_top)
        self.textbox.bind("<KeyPress-Prior>", self._on_key_top)  # RePag

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def set_text(self, texto: str):
        """Carga un texto completo desde cero (paginación invertida).

        Solo renderiza las últimas páginas y salta al final.
        """
        self.texto_completo = texto or ""
        self._paginas = _dividir_en_paginas(self.texto_completo)
        # Renderiza las últimas páginas (las más recientes).
        primera = max(0, len(self._paginas) - PAGE_CARGADAS_INICIAL)
        self._render(primera)
        self._ir_al_final()

    def append_text(self, texto_nuevo: str):
        """Añade texto nuevo al final (transcripción en vivo).

        Actualiza la fuente de verdad y, si el usuario está viendo el
        final (lo habitual al grabar), re-renderiza únicamente las últimas
        páginas y se mantiene pegado al final.
        """
        if not texto_nuevo:
            return
        self.texto_completo += texto_nuevo
        # ¿Está el usuario cerca del final?
        en_final = self._esta_en_final()
        self._paginas = _dividir_en_paginas(self.texto_completo)
        # Renderiza de nuevo las últimas páginas (solo unas pocas → barato).
        primera = max(0, len(self._paginas) - PAGE_CARGADAS_INICIAL)
        self._render(primera)
        if en_final:
            self._ir_al_final()

    def _esta_en_final(self) -> bool:
        try:
            y0, _y1 = self.textbox.yview()
            return y0 >= 1.0 - UMBRAL_TOPE
        except Exception:
            return True

    # ------------------------------------------------------------------
    # Renderizado
    # ------------------------------------------------------------------
    def _render(self, idx_inicio: int):
        """Reemplaza el widget con las páginas desde ``idx_inicio``."""
        self._idx_inicio = max(0, min(idx_inicio, len(self._paginas) - 1)) \
            if self._paginas else 0
        contenido = "\n".join(self._paginas[self._idx_inicio:])
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.insert("1.0", contenido + ("\n" if contenido else ""))
        self.textbox.configure(state="disabled")

    def _ir_al_final(self):
        try:
            self.textbox.see("end")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Carga de páginas anteriores (scroll hacia arriba)
    # ------------------------------------------------------------------
    def _cargar_mas_arriba(self):
        if self._idx_inicio <= 0:
            return  # ya está todo cargado
        nueva = self._idx_inicio - 1
        bloque = self._paginas[nueva] + "\n"

        # Anclamos la línea que está visible en el tope para poder volver a
        # ella tras insertar la página anterior arriba.
        ancla = self.textbox.index("@0,0")
        di_antes = self.textbox._textbox.dlineinfo(ancla)
        y_antes = di_antes[1] if di_antes else 0

        # Insertamos el bloque nuevo al inicio del widget.
        self.textbox.configure(state="normal")
        self.textbox.insert("1.0", bloque)
        self.textbox.configure(state="disabled")
        self.textbox.update_idletasks()

        # Llevamos el ancla de vuelta al viewport y ajustamos en píxeles
        # para que el salto visual sea mínimo (con wrap="word" cada página
        # ocupa varias líneas de pantalla).
        self.textbox.see(ancla)
        self.textbox.update_idletasks()
        di_despues = self.textbox._textbox.dlineinfo(ancla)
        if di_despues:
            y_despues = di_despues[1]
            altura_linea = di_despues[3] or 1
            delta_px = y_despues - y_antes
            lineas = int(delta_px / altura_linea)
            if lineas:
                self.textbox.yview("scroll", lineas, "units")
            self.textbox.update_idletasks()

        self._idx_inicio = nueva

    def _on_wheel(self, event):
        """Detecta scroll hacia arriba para cargar más páginas antiguas."""
        # Si ya está todo cargado, no hacemos nada.
        if self._idx_inicio <= 0:
            return
        # En Windows, delta>0 = scroll hacia arriba.
        hacia_arriba = event.num in (4,) or (hasattr(event, "delta") and event.delta > 0)
        if hacia_arriba:
            try:
                y0, _y1 = self.textbox.yview()
                if y0 <= UMBRAL_TOPE:
                    self._cargar_mas_arriba()
            except Exception:
                pass

    def _on_key_top(self, _event):
        """Carga más páginas si el usuario pulsa RePag/Arriba en el tope."""
        if self._idx_inicio <= 0:
            return
        try:
            y0, _y1 = self.textbox.yview()
            if y0 <= UMBRAL_TOPE:
                self._cargar_mas_arriba()
        except Exception:
            pass
