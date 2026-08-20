"""Renderizador básico de Markdown para CustomTkinter."""

import re
import customtkinter as ctk
from tkinter import font
from ui.theme import colors


class MarkdownRenderer:
    """Renderiza texto Markdown en un CTkTextbox con estilos."""

    # Patrones de Markdown - usando diccionario
    PATTERNS = {
        "heading1": re.compile(r'^# (.+)$'),
        "heading2": re.compile(r'^## (.+)$'),
        "heading3": re.compile(r'^### (.+)$'),
        "bold": re.compile(r'\*\*(.+?)\*\*'),
        "italic": re.compile(r'\*(.+?)\*'),
        "italic_alt": re.compile(r'_(.+?)_'),
        "code": re.compile(r'`(.+?)`'),
        "code_block": re.compile(r'```(.+?)```', re.DOTALL),
        "quote": re.compile(r'^> (.+)$'),
        "list": re.compile(r'^[\-\*\+] (.+)$'),
        "numbered": re.compile(r'^\d+\. (.+)$'),
        "link": re.compile(r'\[(.+?)\]\((.+?)\)'),
        "horizontal_rule": re.compile(r'^---$'),
    }

    # Estilos para tags de Tkinter
    STYLES = {
        "h1": {"size": 22, "weight": "bold", "spacing3": 12},
        "h2": {"size": 18, "weight": "bold", "spacing3": 8},
        "h3": {"size": 15, "weight": "bold", "spacing3": 6},
        "bold": {"weight": "bold"},
        "italic": {"slant": "italic"},
        "code": {"family": "Consolas", "foreground": "#f8f8f2", "background": "#2d2d2d"},
        "code_block": {"family": "Consolas", "foreground": "#f8f8f2", "background": "#1a1a1a"},
        "quote": {"foreground": colors.text_muted, "slant": "italic"},
        "list": {"foreground": colors.text_secondary},
        "numbered": {"foreground": colors.text_secondary},
        "link": {"foreground": colors.accent, "underline": True},
        "horizontal_rule": {"foreground": colors.border},
    }

    def __init__(self, textbox: ctk.CTkTextbox):
        self.textbox = textbox
        self._configure_tags()

    def _configure_tags(self):
        """Configura los tags para los estilos."""
        # Acceder al Text interno de CTkTextbox
        textbox = self.textbox._textbox

        # Limpiar tags existentes (excepto los predeterminados de Tkinter)
        default_tags = {"sel", "end", "start", "tk::unspecified1", "tk::unspecified2"}
        for tag in textbox.tag_names():
            if tag not in default_tags:
                try:
                    textbox.tag_delete(tag)
                except Exception:
                    pass

        # Crear tags con estilos
        for name, style in self.STYLES.items():
            tag_config = {}
            
            # Configurar fuente
            font_kwargs = {}
            if "size" in style:
                font_kwargs["size"] = style["size"]
            if "weight" in style:
                font_kwargs["weight"] = style["weight"]
            if "slant" in style:
                font_kwargs["slant"] = style["slant"]
            if "family" in style:
                font_kwargs["family"] = style["family"]
            
            if font_kwargs:
                tag_config["font"] = font.Font(**font_kwargs)
            
            # Configurar colores
            if "foreground" in style:
                tag_config["foreground"] = style["foreground"]
            if "background" in style:
                tag_config["background"] = style["background"]
            
            # Otras propiedades
            if "underline" in style:
                tag_config["underline"] = style["underline"]
            if "spacing3" in style:
                tag_config["spacing3"] = style["spacing3"]

            try:
                textbox.tag_configure(name, **tag_config)
            except Exception as e:
                print(f"Error configurando tag {name}: {e}")

        # Tag especial para el párrafo en edición
        try:
            textbox.tag_configure(
                "editing", 
                background=colors.bg_panel_light, 
                spacing3=2,
                relief="sunken",
                borderwidth=1
            )
        except Exception:
            pass

    def render(self, text: str, editing_start: int = None, editing_end: int = None):
        """Renderiza texto Markdown en el textbox."""
        textbox = self.textbox._textbox
        
        try:
            textbox.configure(state="normal")
        except Exception:
            pass
        
        textbox.delete("1.0", "end")

        if not text:
            try:
                textbox.configure(state="disabled")
            except Exception:
                pass
            return

        lines = text.split("\n")
        
        # Procesar línea por línea
        for line in lines:
            # Detectar tipo de línea
            line_type, content = self._detect_line_type(line)

            if line_type and content is not None:
                self._insert_formatted_line(content, line_type)
            else:
                # Texto normal con formato inline
                self._insert_inline_formatted(line)

            # Insertar salto de línea
            textbox.insert("end", "\n")

        # Aplicar tag de edición si está definido
        if editing_start is not None and editing_end is not None and editing_start < editing_end:
            try:
                start_index = f"1.0 + {editing_start} chars"
                end_index = f"1.0 + {editing_end} chars"
                textbox.tag_add("editing", start_index, end_index)
            except Exception as e:
                print(f"Error aplicando tag de edición: {e}")

        try:
            textbox.configure(state="disabled")
        except Exception:
            pass

    def _detect_line_type(self, line: str):
        """Detecta el tipo de línea Markdown."""
        line = line.rstrip()
        
        if not line:
            return None, None

        # Encabezados
        for i in range(1, 4):
            pattern = self.PATTERNS.get(f"heading{i}")
            if pattern:
                match = pattern.match(line)
                if match:
                    return f"h{i}", match.group(1)

        # Cita
        pattern = self.PATTERNS.get("quote")
        if pattern:
            match = pattern.match(line)
            if match:
                return "quote", match.group(1)

        # Lista
        pattern = self.PATTERNS.get("list")
        if pattern:
            match = pattern.match(line)
            if match:
                return "list", match.group(1)

        # Lista numerada
        pattern = self.PATTERNS.get("numbered")
        if pattern:
            match = pattern.match(line)
            if match:
                return "numbered", match.group(1)

        # Línea horizontal
        pattern = self.PATTERNS.get("horizontal_rule")
        if pattern:
            if pattern.match(line):
                return "horizontal_rule", "─" * 40

        return None, line

    def _insert_formatted_line(self, content: str, line_type: str):
        """Inserta una línea con formato específico."""
        textbox = self.textbox._textbox
        
        # Aplicar formato inline dentro de la línea
        self._insert_inline_formatted(content, base_tag=line_type)

    def _insert_inline_formatted(self, text: str, base_tag: str = None):
        """Inserta texto con formato inline (negrita, cursiva, código, enlaces)."""
        if not text:
            return
            
        textbox = self.textbox._textbox
        
        # Primero procesar enlaces
        link_pattern = self.PATTERNS.get("link")
        if link_pattern:
            match = link_pattern.search(text)
            if match:
                # Texto antes del enlace
                before = text[:match.start()]
                if before:
                    self._insert_with_inline_formatting(before, base_tag)
                
                # Insertar enlace
                link_text = match.group(1)
                link_url = match.group(2)  # URL disponible pero no usada en la vista
                
                tags = ("link", base_tag) if base_tag else "link"
                textbox.insert("end", link_text, tags)
                
                # Resto del texto
                after = text[match.end():]
                if after:
                    self._insert_inline_formatted(after, base_tag)
                return

        # Procesar el texto sin enlaces
        self._insert_with_inline_formatting(text, base_tag)

    def _insert_with_inline_formatting(self, text: str, base_tag: str = None):
        """Inserta texto aplicando formato inline (negrita, cursiva, código)."""
        if not text:
            return
            
        textbox = self.textbox._textbox

        # Procesar negrita
        bold_pattern = self.PATTERNS.get("bold")
        if bold_pattern:
            match = bold_pattern.search(text)
            if match:
                before = text[:match.start()]
                bold_text = match.group(1)
                after = text[match.end():]

                if before:
                    self._insert_with_inline_formatting(before, base_tag)

                tags = ("bold", base_tag) if base_tag else "bold"
                textbox.insert("end", bold_text, tags)

                if after:
                    self._insert_with_inline_formatting(after, base_tag)
                return

        # Procesar cursiva
        italic_pattern = self.PATTERNS.get("italic")
        if italic_pattern:
            match = italic_pattern.search(text)
            if match:
                before = text[:match.start()]
                italic_text = match.group(1)
                after = text[match.end():]

                if before:
                    self._insert_with_inline_formatting(before, base_tag)

                tags = ("italic", base_tag) if base_tag else "italic"
                textbox.insert("end", italic_text, tags)

                if after:
                    self._insert_with_inline_formatting(after, base_tag)
                return

        # Procesar código inline
        code_pattern = self.PATTERNS.get("code")
        if code_pattern:
            match = code_pattern.search(text)
            if match:
                before = text[:match.start()]
                code_text = match.group(1)
                after = text[match.end():]

                if before:
                    self._insert_with_inline_formatting(before, base_tag)

                tags = ("code", base_tag) if base_tag else "code"
                textbox.insert("end", code_text, tags)

                if after:
                    self._insert_with_inline_formatting(after, base_tag)
                return

        # Texto plano
        if base_tag:
            textbox.insert("end", text, base_tag)
        else:
            textbox.insert("end", text)


class MarkdownView(ctk.CTkFrame):
    """Widget que muestra texto Markdown con soporte para edición en línea."""

    def __init__(self, master, **kwargs):
        super().__init__(master, fg_color=colors.bg_panel, **kwargs)
        self._renderer = None
        self._text = ""
        self._editing_start = None
        self._editing_end = None
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Crear el textbox con borde
        container = ctk.CTkFrame(
            self,
            fg_color=colors.bg_panel_light,
            border_width=1,
            border_color=colors.border,
        )
        container.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        container.grid_columnconfigure(0, weight=1)
        container.grid_rowconfigure(0, weight=1)

        self.textbox = ctk.CTkTextbox(
            container,
            fg_color=colors.bg_panel_light,
            text_color=colors.text_primary,
            border_width=0,
            font=ctk.CTkFont(size=13),
            wrap="word",
        )
        self.textbox.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        self._renderer = MarkdownRenderer(self.textbox)

    def set_text(self, text: str, editing_start: int = None, editing_end: int = None):
        """Establece el texto y lo renderiza con Markdown."""
        self._text = text or ""
        self._editing_start = editing_start
        self._editing_end = editing_end
        self._renderer.render(self._text, editing_start, editing_end)

    def get_text(self) -> str:
        """Obtiene el texto fuente (Markdown original).

        Devolvemos ``self._text`` (el texto fuente intacto) en lugar del
        contenido del widget renderizado, porque el renderizador elimina
        los marcadores Markdown (``##``, ``**``, ``-``, etc.) al dibujar.
        Si se leyera el widget, se perdería el formato al guardar.
        """
        return self._text or ""

    def set_editing_range(self, start: int, end: int):
        """Establece el rango del párrafo que se está editando."""
        self._editing_start = start
        self._editing_end = end
        self.set_text(self._text, start, end)