"""Panel de los 4 sectores informativos (resumen, datos, glosario, cuerpo).

Se presenta como pestañas editables dentro de la hoja de transcripción.
"""
import customtkinter as ctk

from models.chapter import Chapter

BG = "#121212"
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
    """Muestra y permite editar los 4 sectores del capítulo."""

    def __init__(self, master, chapter: Chapter):
        super().__init__(master, fg_color=PANEL, corner_radius=10)
        self.chapter = chapter
        self._boxes: dict[str, ctk.CTkTextbox] = {}

        self._build()

    def _build(self):
        # Pestañas
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

        # Contenedor de los textboxes
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
            box.insert("1.0", self.chapter.sectors.get(clave, ""))
            box.pack(fill="both", expand=True)
            self._boxes[clave] = box

        self.tabs.set(SECTORES[0][1])
        self._show(SECTORES[0][1])

    def _show(self, nombre):
        for clave, etiqueta in SECTORES:
            if nombre == etiqueta:
                self._boxes[clave].pack(fill="both", expand=True)
                self._boxes[clave].tkraise()
            else:
                self._boxes[clave].pack_forget()

    def sync_from_chapter(self):
        """Recarga la UI desde el capítulo (tras transcripción rápida)."""
        for clave, _nombre in SECTORES:
            self._boxes[clave].delete("1.0", "end")
            self._boxes[clave].insert("1.0", self.chapter.sectors.get(clave, ""))

    def sync_to_chapter(self):
        """Guarda lo que hay en la UI hacia el capítulo."""
        for clave, _nombre in SECTORES:
            self.chapter.sectors[clave] = self._boxes[clave].get("1.0", "end").strip()
