"""Panel de subventanas del cuerpo de un capítulo.

La hoja derecha (el "cuerpo") se muestra como subventanas/pestañas, una
por cada sección de la nota:

- Resumen
- Datos importantes
- Glosario
- Cuerpo (el texto transcrito, que reemplazó al antiguo sector "cuerpo")

Las tres primeras se guardan en ``chapter.sectors``; la pestaña "Cuerpo"
guarda directamente en ``chapter.transcribed_text``. De este modo todo
se ve y se edita dentro del propio cuerpo, sin paneles externos.
"""
import customtkinter as ctk

from models.chapter import Chapter

PANEL = "#1e1e1e"
PANEL2 = "#2a2a2a"
ACCENTO = "#6c5ce7"
TEXTO = "#e8e8e8"
SUBTEXTO = "#9a9a9a"

SECTORES = (
    ("resumen", "Resumen"),
    ("datos_importantes", "Datos importantes"),
    ("glosario", "Glosario"),
    ("cuerpo", "Cuerpo"),
)


class SectorsPanel(ctk.CTkFrame):
    """Muestra y permite editar los sectores como subventanas del cuerpo."""

    def __init__(self, master, chapter: Chapter):
        super().__init__(master, fg_color=PANEL, corner_radius=10)
        self.chapter = chapter
        self._boxes: dict[str, ctk.CTkTextbox] = {}

        self._build()

    def _build(self):
        # Pestañas (subventanas del cuerpo)
        self.tabs = ctk.CTkSegmentedButton(
            self,
            values=[nombre for _clave, nombre in SECTORES],
            selected_color=ACCENTO,
            selected_hover_color="#5a4bd1",
            text_color=TEXTO,
            font=ctk.CTkFont(size=12),
            command=self._show,
        )
        self.tabs.pack(fill="x", padx=8, pady=(8, 4))

        # Contenedor de las cajas de texto
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        for clave, nombre in SECTORES:
            box = ctk.CTkTextbox(
                self.container,
                fg_color=PANEL2, text_color=TEXTO,
                border_width=1, border_color=PANEL,
                font=ctk.CTkFont(size=13),
                wrap="word",
            )
            box.insert("1.0", self._valor(clave))
            box.pack(fill="both", expand=True)
            self._boxes[clave] = box

        self.tabs.set(SECTORES[-1][1])
        self._show(SECTORES[-1][1])

    # ------------------------------------------------------------------
    # Lectura/escritura de cada sección
    # ------------------------------------------------------------------
    def _valor(self, clave: str) -> str:
        """Devuelve el texto actual de una sección desde el capítulo."""
        if clave == "cuerpo":
            return self.chapter.transcribed_text
        return self.chapter.sectors.get(clave, "")

    def _asignar(self, clave: str, texto: str) -> None:
        """Guarda el texto de una sección en el capítulo."""
        if clave == "cuerpo":
            self.chapter.transcribed_text = texto
        else:
            self.chapter.sectors[clave] = texto

    # ------------------------------------------------------------------
    def _show(self, nombre):
        for clave, etiqueta in SECTORES:
            if nombre == etiqueta:
                self._boxes[clave].pack(fill="both", expand=True)
                self._boxes[clave].tkraise()
            else:
                self._boxes[clave].pack_forget()

    def sync_from_chapter(self):
        """Recarga la UI desde el capítulo (tras la transcripción completa)."""
        for clave, _nombre in SECTORES:
            self._boxes[clave].delete("1.0", "end")
            self._boxes[clave].insert("1.0", self._valor(clave))

    def sync_to_chapter(self):
        """Guarda lo que hay en la UI hacia el capítulo."""
        for clave, _nombre in SECTORES:
            self._asignar(clave, self._boxes[clave].get("1.0", "end").strip())
