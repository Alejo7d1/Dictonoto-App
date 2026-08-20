"""Panel de subventanas del cuerpo de un capítulo."""

import customtkinter as ctk
from models.chapter import Chapter
from ui.theme import colors, spacing, radius, get_font
from ui.components.markdown_renderer import MarkdownView

SECTORES = (
    ("resumen", "📝 Resumen"),
    ("datos_importantes", "📊 Datos importantes"),
    ("glosario", "📚 Glosario"),
    ("cuerpo", "📄 Cuerpo"),
)


class SectorsPanel(ctk.CTkFrame):
    """Muestra y permite editar los sectores como subventanas."""

    def __init__(self, master, chapter: Chapter):
        super().__init__(master, fg_color=colors.bg_panel, corner_radius=radius.lg)
        self.chapter = chapter
        self._boxes: dict[str, ctk.CTkTextbox] = {}
        self._markdown_views: dict[str, MarkdownView] = {}

        # Modo de edición (por defecto False - vista)
        self._edit_mode = False
        self._editing_paragraph_start = None
        self._editing_paragraph_end = None

        self._build()

    # ------------------------------------------------------------------
    def _build(self):
        # Pestañas
        self._build_tabs()

        # Contenedor de texto
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=spacing.sm, pady=(0, spacing.sm))

        # Barra de herramientas (modo edición)
        self._build_toolbar()

        # Contenedor de las vistas
        self._build_views()

        # Seleccionar pestaña por defecto
        self.tabs.set(SECTORES[-1][1])
        self._show(SECTORES[-1][1])

    # ------------------------------------------------------------------
    def _build_tabs(self):
        """Construye el segmented button de pestañas."""
        self.tabs = ctk.CTkSegmentedButton(
            self,
            values=[nombre for _, nombre in SECTORES],
            selected_color=colors.accent,
            selected_hover_color=colors.accent_hover,
            text_color=colors.text_primary,
            font=get_font("body_small"),
            command=self._show,
        )
        self.tabs.pack(fill="x", padx=spacing.sm, pady=(spacing.sm, spacing.xs))

    # ------------------------------------------------------------------
    def _build_toolbar(self):
        """Construye la barra de herramientas de edición."""
        toolbar = ctk.CTkFrame(self.container, fg_color="transparent")
        toolbar.pack(fill="x", pady=(0, spacing.xs))

        # Botón toggle edición
        self.edit_btn = ctk.CTkButton(
            toolbar,
            text="✎ Editar párrafo",
            width=120,
            height=28,
            fg_color=colors.accent,
            hover_color=colors.accent_hover,
            text_color=colors.text_inverse,
            font=get_font("body_small"),
            command=self._toggle_edit_mode,
        )
        self.edit_btn.pack(side="left", padx=spacing.xs)

        # Indicador de modo
        self.mode_label = ctk.CTkLabel(
            toolbar,
            text="🔍 Modo vista",
            text_color=colors.text_muted,
            font=get_font("caption"),
        )
        self.mode_label.pack(side="left", padx=spacing.xs)

        # Botón aplicar cambios
        self.apply_btn = ctk.CTkButton(
            toolbar,
            text="✓ Aplicar",
            width=80,
            height=28,
            fg_color=colors.success,
            hover_color=colors.success_dark,
            text_color=colors.text_inverse,
            font=get_font("body_small"),
            command=self._apply_edits,
        )
        self.apply_btn.pack(side="right", padx=spacing.xs)
        self.apply_btn.pack_forget()  # Oculto por defecto

    # ------------------------------------------------------------------
    def _build_views(self):
        """Construye las vistas para cada sector."""
        view_container = ctk.CTkFrame(self.container, fg_color="transparent")
        view_container.pack(fill="both", expand=True)

        for clave, nombre in SECTORES:
            # Vista Markdown (renderizada)
            markdown_view = MarkdownView(view_container)
            markdown_view.pack(fill="both", expand=True)

            # Textbox de edición (oculto por defecto)
            edit_box = ctk.CTkTextbox(
                view_container,
                fg_color=colors.bg_panel_light,
                text_color=colors.text_primary,
                border_width=1,
                border_color=colors.accent,
                font=get_font("body"),
                wrap="word",
            )
            edit_box.pack(fill="both", expand=True)

            # Cargar contenido
            markdown_view.set_text(self._valor(clave))
            edit_box.insert("1.0", self._valor(clave))

            # Ocultar edit_box por defecto
            edit_box.pack_forget()

            self._markdown_views[clave] = markdown_view
            self._boxes[clave] = edit_box

    # ------------------------------------------------------------------
    def _toggle_edit_mode(self):
        """Alterna entre modo vista y modo edición."""
        self._edit_mode = not self._edit_mode

        # Obtener la clave actual
        current_tab = self.tabs.get()
        clave = self._get_clave_from_nombre(current_tab)

        if self._edit_mode:
            # Cambiar a modo edición
            self.edit_btn.configure(text="✖ Cancelar", fg_color=colors.danger)
            self.mode_label.configure(text="✎ Editando párrafo…", text_color=colors.warning)
            self.apply_btn.pack(side="right", padx=spacing.xs)

            # Mostrar edit_box, ocultar markdown
            self._markdown_views[clave].pack_forget()
            self._boxes[clave].pack(fill="both", expand=True)

            # Cargar texto actual en edit_box
            current_text = self._valor(clave)
            self._boxes[clave].delete("1.0", "end")
            self._boxes[clave].insert("1.0", current_text)

            # Encontrar el párrafo bajo el cursor
            self._find_paragraph_under_cursor()

        else:
            # Volver a modo vista (cancelar)
            self._exit_edit_mode()

    # ------------------------------------------------------------------
    def _exit_edit_mode(self):
        """Sale del modo edición sin guardar."""
        self._edit_mode = False
        self.edit_btn.configure(text="✎ Editar párrafo", fg_color=colors.accent)
        self.mode_label.configure(text="🔍 Modo vista", text_color=colors.text_muted)
        self.apply_btn.pack_forget()

        # Obtener la clave actual
        current_tab = self.tabs.get()
        clave = self._get_clave_from_nombre(current_tab)

        # Mostrar markdown, ocultar edit_box
        self._boxes[clave].pack_forget()
        self._markdown_views[clave].pack(fill="both", expand=True)

    # ------------------------------------------------------------------
    def _find_paragraph_under_cursor(self):
        """Encuentra el párrafo actual para resaltarlo."""
        # Esto se puede implementar con detección de clic o posición del cursor
        # Por ahora, simplemente resaltamos el primer párrafo
        text = self._valor(self._get_clave_actual())
        if not text:
            return

        # Dividir en párrafos
        paragraphs = text.split("\n\n")
        if not paragraphs:
            return

        # Marcar el primer párrafo como editable
        para = paragraphs[0]
        start = text.find(para)
        end = start + len(para)

        self._editing_paragraph_start = start
        self._editing_paragraph_end = end

        # Actualizar la vista Markdown con resaltado
        self._markdown_views[self._get_clave_actual()].set_text(
            text,
            self._editing_paragraph_start,
            self._editing_paragraph_end
        )

    # ------------------------------------------------------------------
    def _apply_edits(self):
        """Aplica los cambios del párrafo editado."""
        clave = self._get_clave_actual()
        edit_text = self._boxes[clave].get("1.0", "end-1c")

        # Obtener el texto completo actual
        full_text = self._valor(clave)

        if self._editing_paragraph_start is not None and self._editing_paragraph_end is not None:
            # Reemplazar solo el párrafo editado
            new_text = (
                full_text[:self._editing_paragraph_start] +
                edit_text +
                full_text[self._editing_paragraph_end:]
            )
        else:
            new_text = edit_text

        # Guardar
        self._asignar(clave, new_text)

        # Actualizar vista
        self._markdown_views[clave].set_text(new_text)
        self._boxes[clave].delete("1.0", "end")
        self._boxes[clave].insert("1.0", new_text)

        # Salir del modo edición
        self._exit_edit_mode()

    # ------------------------------------------------------------------
    def _get_clave_actual(self) -> str:
        """Obtiene la clave del sector actual."""
        current_tab = self.tabs.get()
        return self._get_clave_from_nombre(current_tab)

    def _get_clave_from_nombre(self, nombre: str) -> str:
        """Convierte nombre de pestaña a clave."""
        for clave, etiqueta in SECTORES:
            if etiqueta == nombre:
                return clave
        return "cuerpo"

    # ------------------------------------------------------------------
    def _valor(self, clave: str) -> str:
        """Devuelve el texto actual de una sección."""
        if clave == "cuerpo":
            return self.chapter.transcribed_text
        return self.chapter.sectors.get(clave, "")

    def _asignar(self, clave: str, texto: str) -> None:
        """Guarda el texto de una sección."""
        if clave == "cuerpo":
            self.chapter.transcribed_text = texto
        else:
            self.chapter.sectors[clave] = texto

    # ------------------------------------------------------------------
    def _show(self, nombre: str):
        """Muestra la pestaña seleccionada."""
        # Si estamos en modo edición, salir primero
        if self._edit_mode:
            self._exit_edit_mode()

        for clave, etiqueta in SECTORES:
            if nombre == etiqueta:
                self._markdown_views[clave].pack(fill="both", expand=True)
                self._markdown_views[clave].tkraise()
                self._boxes[clave].pack_forget()
            else:
                self._markdown_views[clave].pack_forget()

    # ------------------------------------------------------------------
    def sync_from_chapter(self):
        """Recarga la UI desde el capítulo."""
        for clave, _ in SECTORES:
            text = self._valor(clave)
            self._markdown_views[clave].set_text(text)
            self._boxes[clave].delete("1.0", "end")
            self._boxes[clave].insert("1.0", text)

        # Si estábamos en modo edición, salir
        if self._edit_mode:
            self._exit_edit_mode()

    def sync_to_chapter(self):
        """Guarda la UI hacia el capítulo."""
        # Solo guardar si no estamos en modo edición
        if not self._edit_mode:
            for clave, _ in SECTORES:
                # Obtener texto de la vista markdown
                text = self._markdown_views[clave].get_text()
                self._asignar(clave, text)

    def get_text(self, clave: str) -> str:
        """Obtiene el texto de un sector específico."""
        return self._markdown_views[clave].get_text()