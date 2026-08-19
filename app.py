"""Controlador principal de Dictonoto.

Orquesta la biblioteca, los libros/capítulos, la grabación de audio, la
transcripción local en vivo y la IA (transcripción completa). Es el
puente entre la UI y las capas de servicio.
"""
import threading

import customtkinter as ctk

from config.config_manager import ConfigManager
from core.ai_service import AIService
from core.library import LibraryManager
from core.recorder import AudioRecorder
from core.transcriber import Transcriber
from models.book import Book
from ui.components.chapter_view import ChapterView
from ui.components.library_view import LibraryView
from ui.views.ai_config_view import AIConfigView
from ui.views.book_view import BookView
from ui.views.chapter_manager_view import ChapterManagerView

BG = "#121212"
PANEL = "#1e1e1e"
ACCENTO = "#6c5ce7"
TEXTO = "#e8e8e8"
SUBTEXTO = "#9a9a9a"


def _escape_html(texto: str) -> str:
    """Escapa caracteres XML/HTML para que ``Paragraph`` de reportlab no
    los interprete ni falle (p. ej. con `<`, `&` o `>`)."""
    texto = texto.replace("&", "&amp;")
    texto = texto.replace("<", "&lt;")
    texto = texto.replace(">", "&gt;")
    return texto


class DictonotoApp(ctk.CTk):
    """Ventana principal de la aplicación."""

    def __init__(self):
        super().__init__()
        self.title("Dictonoto — Transcripción en tiempo real")
        self.geometry("1180x760")
        self.minsize(980, 600)
        self.configure(fg_color=BG)

        # Servicios
        self.config = ConfigManager()
        self.library = LibraryManager()
        self.ai = AIService(self.config)
        self.transcriber = Transcriber(
            self.config.get("recording", "whisper_model", "small"),
            device=self.config.get("recording", "device", "auto"),
        )
        self.recorder = AudioRecorder(
            input_device=self.config.get("recording", "input_device", None)
        )
        self.recorder.silence_pause_seconds = float(
            self.config.get("recording", "silence_pause_seconds", 6)
        )
        self.recorder.max_fragment_seconds = float(
            self.config.get("recording", "max_fragment_seconds", 12)
        )
        self.recorder.auto_quick_transcription = bool(
            self.config.get("recording", "auto_quick_transcription", True)
        )
        self.recorder.on_quick_fragment = self._on_quick_fragment
        self.recorder.on_volume_level = self._on_volume_level

        # Estado de navegación
        self.current_book: Book | None = None
        self.current_chapter = None
        self.chapter_view: ChapterView | None = None

        # Hilo de trabajo para transcripciones (evita congelar la UI)
        self.work_queue = []
        self._work_lock = threading.Lock()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

        # Barra superior
        self._build_topbar()

        # Contenedor de vistas
        self.view_container = ctk.CTkFrame(self, fg_color="transparent")
        self.view_container.pack(fill="both", expand=True)
        self.view_container.grid_columnconfigure(0, weight=1)
        self.view_container.grid_rowconfigure(0, weight=1)

        self._show_library()

    # ==================================================================
    # Barra superior
    # ==================================================================
    def _build_topbar(self):
        top = ctk.CTkFrame(self, fg_color=PANEL, corner_radius=0, height=52)
        top.pack(fill="x")
        top.pack_propagate(False)

        ctk.CTkLabel(
            top, text="📓 Dictonoto",
            font=ctk.CTkFont(size=17, weight="bold"), text_color=TEXTO,
        ).pack(side="left", padx=14)

        ctk.CTkButton(
            top, text="⚙ Ajustes", width=130,
            fg_color="transparent", hover_color="#2a2a2a",
            text_color=TEXTO, command=self._abrir_config_ia,
        ).pack(side="right", padx=10)

    # ==================================================================
    # Navegación entre vistas
    # ==================================================================
    def _clear_view(self):
        for w in self.view_container.winfo_children():
            w.destroy()
        self.chapter_view = None

    def _show_library(self):
        self._clear_view()
        self.current_book = None
        self.current_chapter = None

        libros = self.library.list_books()
        vista = LibraryView(
            self.view_container,
            libros,
            on_new_book=lambda: self._show_book_form(),
            on_edit_book=lambda l: self._show_book_form(l),
            on_delete_book=self._eliminar_libro,
            on_open_book=self._open_book,
        )
        vista.grid(row=0, column=0, sticky="nsew")

    def _show_book_form(self, libro=None):
        """Muestra la página para crear/editar un libro (inline)."""
        self._clear_view()
        vista = BookView(
            self.view_container,
            libro,
            on_saved=self._on_book_saved,
            on_back=self._show_library,
            on_delete=self._confirmar_eliminar_libro,
        )
        vista.grid(row=0, column=0, sticky="nsew")

    def _show_chapter_manager(self, libro=None):
        """Muestra la página de gestión de capítulos (inline)."""
        if libro is None:
            libro = self.current_book
        if libro is None:
            self._show_library()
            return
        self._clear_view()
        vista = ChapterManagerView(
            self.view_container,
            libro,
            on_open_chapter=self._open_chapter,
            on_back=self._show_library,
        )
        vista.grid(row=0, column=0, sticky="nsew")

    def _show_ai_config(self):
        """Muestra la página de configuración de IA (inline)."""
        self._clear_view()
        vista = AIConfigView(
            self.view_container,
            self.config,
            on_saved=self._reload_ai,
            on_back=self._volver_desde_config,
        )
        vista.grid(row=0, column=0, sticky="nsew")

    def _volver_desde_config(self):
        """Vuelve a la vista anterior a la configuración."""
        if self.current_chapter is not None:
            # Venía de un capítulo abierto: vuelve a él sin perder estado
            self._show_chapter_view()
        elif self.current_book is not None:
            self._show_chapter_manager(self.current_book)
        else:
            self._show_library()

    def _show_chapter_view(self):
        self._clear_view()
        view = ChapterView(
            self.view_container,
            self.current_chapter,
            on_toggle_record=self._toggle_record,
            on_full_transcription=self._run_full_transcription,
            on_export=self._exportar_md,
            on_export_pdf=self._exportar_pdf,
            on_save=self._guardar_actual,
            on_back=self._open_book,
        )
        view.grid(row=0, column=0, sticky="nsew")
        self.chapter_view = view

    # ==================================================================
    # Gestión de libros
    # ==================================================================
    def _on_book_saved(self, libro, eliminar=False):
        if eliminar:
            self._delete_book_file(libro)
        else:
            self.library.save_book(libro)
        self._show_library()

    def _confirmar_eliminar_libro(self, libro):
        """Confirmación (alerta) y borrado desde la página del libro."""
        self._eliminar_libro(libro)

    def _eliminar_libro(self, libro):
        if self._confirmar("Eliminar libro",
                           f"¿Eliminar «{libro.name}» y todos sus capítulos?"):
            self._delete_book_file(libro)
            self._show_library()

    def _delete_book_file(self, libro):
        import os
        safe = "".join(c for c in libro.name if c not in '\\/:*?"<>|')
        safe = safe.strip().replace(" ", "_") or "libro"
        path = os.path.join("data/books", f"{safe}.json")
        if os.path.exists(path):
            os.remove(path)

    def _confirmar(self, titulo, mensaje) -> bool:
        import customtkinter as ctk
        dlg = ctk.CTkToplevel(self)
        dlg.title(titulo)
        dlg.geometry("380x180")
        dlg.configure(fg_color=BG)
        dlg.grab_set()
        res = {"ok": False}

        ctk.CTkLabel(
            dlg, text=mensaje, text_color=TEXTO, wraplength=340,
            font=ctk.CTkFont(size=14),
        ).pack(pady=(22, 16), padx=16)

        btns = ctk.CTkFrame(dlg, fg_color="transparent")
        btns.pack()

        def ok():
            res["ok"] = True
            dlg.destroy()

        ctk.CTkButton(
            btns, text="Sí", width=110, fg_color="#e74c3c",
            hover_color="#c0392b", text_color="white", command=ok,
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            btns, text="Cancelar", width=110,
            fg_color=PANEL, hover_color="#2a2a2a",
            text_color=TEXTO, command=dlg.destroy,
        ).pack(side="left", padx=6)

        self.wait_window(dlg)
        return res["ok"]

    def _open_book(self, libro=None):
        """Abre la página de gestión de capítulos de un libro."""
        if libro is not None:
            self._refresh_libro(libro)
        else:
            # Vuelta desde el capítulo: guarda antes de dejar la vista
            self._guardar_actual()
            if self.current_book is None:
                return
        self._show_chapter_manager(self.current_book)

    def _refresh_libro(self, libro):
        """Sincroniza current_book y lo recarga desde disco si existe."""
        for l in self.library.list_books():
            if l.name == libro.name:
                self.current_book = l
                return
        # Si no está en disco (nuevo, sin guardar aún) úsalo tal cual
        self.current_book = libro

    def _open_chapter(self, cap):
        self.current_chapter = cap
        self.transcriber.reset_context()  # nuevo capítulo: contexto limpio
        self._show_chapter_view()

    def _guardar_actual(self):
        if self.chapter_view:
            self.chapter_view.persist_from_ui()
        if self.current_book:
            self.library.save_book(self.current_book)
        if self.chapter_view:
            self.chapter_view.set_status("✓ Guardado")

    # ==================================================================
    # Configuración de IA
    # ==================================================================
    def _abrir_config_ia(self):
        self._show_ai_config()

    def _reload_ai(self):
        self.ai = AIService(self.config)
        self.recorder.silence_pause_seconds = float(
            self.config.get("recording", "silence_pause_seconds", 6)
        )
        self.recorder.max_fragment_seconds = float(
            self.config.get("recording", "max_fragment_seconds", 12)
        )
        self.recorder.auto_quick_transcription = bool(
            self.config.get("recording", "auto_quick_transcription", True)
        )
        # Actualiza el dispositivo de entrada configurado
        self.recorder.input_device = self.config.get(
            "recording", "input_device", None
        )
        # Si cambió el modelo Whisper o el dispositivo (GPU/CPU), recárgalo
        modelo = self.config.get("recording", "whisper_model", "small")
        device = self.config.get("recording", "device", "auto")
        if (
            self.transcriber.model_size != modelo
            or self.transcriber.device != device
        ):
            self.transcriber = Transcriber(modelo, device=device)
        self.transcriber.reset_context()
        # Vuelve a la vista anterior tras guardar
        self._volver_desde_config()

    # ==================================================================
    # Grabación
    # ==================================================================
    def _toggle_record(self, recording: bool):
        if recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _start_recording(self):
        # La IA no es imprescindible para la transcripción bruta local.
        # Solo la necesitamos para el formateo posterior, así que grabamos
        # igual y avisamos si no está configurada.
        try:
            self.recorder.start()
            self.chapter_view.set_recording_state(True)
            self.chapter_view.set_volume_level(0.0)  # resetea el medidor
            self.chapter_view.set_status("● Grabando… (cargando Whisper…)")
            # Pre-carga del modelo Whisper en segundo plano para evitar
            # esperas/errores a mitad de grabación.
            self._enqueue_work(self._precargar_whisper)
        except Exception as e:
            self.chapter_view.set_status(f"Error al grabar: {e}")
            self.chapter_view.set_recording_state(False)

    def _on_volume_level(self, nivel: float):
        """Callback del grabador: actualiza el medidor de sonido en vivo.

        Se ejecuta en el hilo de audio; encola la actualización en la UI.
        """
        try:
            self.after(0, lambda nivel=nivel: self._actualizar_medidor(nivel))
        except Exception:
            pass  # la ventana puede estar cerrándose

    def _actualizar_medidor(self, nivel: float):
        if self.chapter_view is not None:
            self.chapter_view.set_volume_level(nivel)

    def _precargar_whisper(self):
        """Carga el modelo Whisper local (puede tardar la primera vez)."""
        try:
            self.transcriber.ensure_loaded()
            self.after(0, lambda: self.chapter_view.set_status("● Grabando…"))
        except Exception as e:
            # e se congela como valor por defecto de la lambda para
            # evitar el late-binding (NameError al ejecutarla después).
            self.after(0, lambda e=e: self._mostrar_error(f"Whisper: {e}"))

    def _stop_recording(self):
        self.chapter_view.set_recording_state(False)
        self.chapter_view.set_status("Procesando audio…")
        self.after(10, self._finalize_recording)

    def _finalize_recording(self):
        """Al detener, transcribe solo el audio que quedó sin pausa.

        Los fragmentos ya se transcribieron en vivo durante la grabación;
        re-transcribir todo el audio aquí SOBRESCRIBIRÍA el texto bruto y
        causaría duplicados. Así que solo procesamos el tramo residual.
        """
        try:
            audio = self.recorder.stop()
            residual = self.recorder.pop_residual_fragment()
            if len(residual) >= self.recorder.samplerate:
                # Transcripción local del tramo residual que quedó sin pausa.
                self._enqueue_work(self._transcibe_rapida, residual)
            else:
                # Sin audio residual relevante.
                self.after(0, lambda: self.chapter_view.set_status(
                    "✓ Grabación detenida"
                ))
        except Exception as e:
            self.chapter_view.set_status(f"Error: {e}")

    # ==================================================================
    # Transcripción en hilo de fondo
    # ==================================================================
    def _enqueue_work(self, func, *args):
        with self._work_lock:
            self.work_queue.append((func, args))

    def _worker_loop(self):
        """Ejecuta tareas de transcripción/IA en un bucle interno."""
        import time
        while True:
            item = None
            with self._work_lock:
                if self.work_queue:
                    item = self.work_queue.pop(0)
            if item:
                func, args = item
                try:
                    func(*args)
                except Exception as e:
                    self.after(0, lambda e=e: self._mostrar_error(str(e)))
            else:
                time.sleep(0.2)

    def _mostrar_error(self, msg):
        if self.chapter_view:
            self.chapter_view.set_status(f"⚠ {msg}")

    # ------------------------------------------------------------------
    def _on_quick_fragment(self, fragmento):
        """Callback del grabador: transcripción en vivo (solo Whisper)."""
        self._enqueue_work(self._transcibe_rapida, fragmento)

    def _transcibe_rapida(self, fragmento):
        """Transcribe un fragmento (Whisper local) y actualiza la hoja bruta.

        Este método corre en el hilo de trabajo y NO llama a la IA: solo
        alimenta el texto bruto en vivo. El formateo con IA se hace al
        pulsar «Transcripción completa» (ver _run_full_transcription).
        """
        try:
            texto = self.transcriber.transcribe(fragmento)
        except Exception as e:
            self.after(0, lambda e=e: self._mostrar_error(f"Whisper: {e}"))
            return
        if not texto:
            return
        if self.current_chapter is None:
            return

        # --- Hoja izquierda: texto bruto en vivo (siempre local) ---
        self.current_chapter.raw_text = (
            self.current_chapter.raw_text
            + (" " if self.current_chapter.raw_text else "")
            + texto
        )
        self.after(0, self._refresh_raw_ui)

    def _refresh_raw_ui(self):
        if self.chapter_view:
            self.chapter_view.sync_after_recording()

    # ------------------------------------------------------------------
    def _run_full_transcription(self):
        """Ejecuta la transcripción completa (reorganiza nota bruta en sectores)."""
        if not self.current_chapter:
            return
        if not self.config.get("ai", "api_key"):
            self.chapter_view.set_status("⚠ Configura la IA primero")
            self._abrir_config_ia()
            return
        if not self.current_chapter.raw_text.strip():
            self.chapter_view.set_status("No hay texto bruto para organizar")
            return
        self.chapter_view.set_status("Organizando con IA…")
        self._enqueue_work(
            self._transcripcion_completa, self.current_chapter
        )

    def _transcripcion_completa(self, chapter):
        try:
            self.ai.full_transcription(chapter)
            self.after(0, self._refresh_chapter_after_full)
        except Exception as e:
            self.after(0, lambda e=e: self._mostrar_error(str(e)))

    def _refresh_chapter_after_full(self):
        if self.chapter_view:
            self.chapter_view.set_transcribed_text(
                self.current_chapter.transcribed_text
            )
            self.chapter_view.sync_sections()
            self.chapter_view.set_status("✓ Transcripción completa lista")

    # ==================================================================
    # Exportación a Markdown
    # ==================================================================
    def _exportar_md(self):
        """Exporta los 4 sectores del capítulo a un único archivo .md.

        El archivo se guarda en ``data/exports`` con el nombre
        ``[Libro - Capítulo].md`` y contiene las secciones Resumen,
        Datos importantes, Glosario y Cuerpo.
        """
        if self.chapter_view:
            self.chapter_view.persist_from_ui()
        if self.current_book is None or self.current_chapter is None:
            self.chapter_view.set_status("⚠ No hay capítulo para exportar")
            return

        nombre_libro = self.current_book.name
        nombre_capitulo = self.current_chapter.title
        ch = self.current_chapter

        partes = [
            f"# {nombre_capitulo}",
            f"**Libro:** {nombre_libro}",
            "",
            "## Resumen",
            ch.sectors.get("resumen", "").strip() or "_Sin contenido_",
            "",
            "## Datos importantes",
            ch.sectors.get("datos_importantes", "").strip() or "_Sin contenido_",
            "",
            "## Glosario",
            ch.sectors.get("glosario", "").strip() or "_Sin contenido_",
            "",
            "## Cuerpo",
            ch.transcribed_text.strip() or "_Sin contenido_",
            "",
        ]
        contenido = "\n".join(partes)

        import os
        os.makedirs("data/exports", exist_ok=True)
        nombre_seguro = (
            "".join(c for c in f"[{nombre_libro} - {nombre_capitulo}]"
                    if c not in '\\/:*?"<>|')
            or "[Capítulo]"
        )
        ruta = os.path.join("data/exports", f"{nombre_seguro}.md")
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)

        self.chapter_view.set_status(f"✓ Exportado: {nombre_seguro}.md")

    def _exportar_pdf(self):
        """Exporta los sectores del capítulo a un archivo PDF formateado.

        Genera un documento PDF (en ``data/exports``) con el título del
        capítulo, el libro y las secciones Resumen, Datos importantes,
        Glosario y Cuerpo, interpretando el Markdown para que no aparezcan
        los marcadores crudos (``*``, ``#``, etc.).
        """
        if self.chapter_view:
            self.chapter_view.persist_from_ui()
        if self.current_book is None or self.current_chapter is None:
            self.chapter_view.set_status("⚠ No hay capítulo para exportar")
            return

        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib.enums import TA_LEFT
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            HRFlowable,
        )
        import markdown

        nombre_libro = self.current_book.name
        nombre_capitulo = self.current_chapter.title
        ch = self.current_chapter

        import os
        os.makedirs("data/exports", exist_ok=True)
        nombre_seguro = (
            "".join(c for c in f"[{nombre_libro} - {nombre_capitulo}]"
                    if c not in '\\/:*?"<>|')
            or "[Capítulo]"
        )
        ruta = os.path.join("data/exports", f"{nombre_seguro}.pdf")

        estilos = {
            "titulo": ParagraphStyle(
                "titulo", fontName="Helvetica-Bold", fontSize=20,
                leading=24, textColor=colors.HexColor("#5a4bd1"),
                spaceAfter=4,
            ),
            "libro": ParagraphStyle(
                "libro", fontName="Helvetica", fontSize=11,
                leading=14, textColor=colors.HexColor("#666666"),
                spaceAfter=10,
            ),
            "h2": ParagraphStyle(
                "h2", fontName="Helvetica-Bold", fontSize=14,
                leading=18, textColor=colors.HexColor("#1e1e1e"),
                spaceBefore=12, spaceAfter=5,
            ),
            "h1": ParagraphStyle(
                "h1", fontName="Helvetica-Bold", fontSize=15,
                leading=19, textColor=colors.HexColor("#333333"),
                spaceBefore=10, spaceAfter=5,
            ),
            "h2i": ParagraphStyle(
                "h2i", fontName="Helvetica-Bold", fontSize=13,
                leading=17, textColor=colors.HexColor("#444444"),
                spaceBefore=10, spaceAfter=5,
            ),
            "h3": ParagraphStyle(
                "h3", fontName="Helvetica-Bold", fontSize=12,
                leading=15, textColor=colors.HexColor("#555555"),
                spaceBefore=8, spaceAfter=4,
            ),
            "cuerpo": ParagraphStyle(
                "cuerpo", fontName="Helvetica", fontSize=11,
                leading=15, textColor=colors.HexColor("#333333"),
                alignment=TA_LEFT, spaceAfter=8,
            ),
            "lista": ParagraphStyle(
                "lista", fontName="Helvetica", fontSize=11,
                leading=15, textColor=colors.HexColor("#333333"),
                alignment=TA_LEFT, spaceAfter=2, leftIndent=8,
            ),
        }

        def md_a_bloques(texto: str):
            """Convierte Markdown en una lista de bloques ``(tipo, html)``.

            Divide el texto en bloques top-level (párrafos, encabezados y
            grupos de listas) separados por líneas en blanco, y convierte
            cada bloque por separado con ``markdown`` para que se respeten
            los saltos entre párrafos y títulos. ``tipo`` indica el estilo
            que debe aplicarse: ``parr``, ``h1``, ``h2``, ``h3`` o ``lista``.
            """
            texto = texto.strip()
            if not texto:
                return [("parr", "<i>Sin contenido</i>")]

            bloques = []
            # Dividir en chunks separados por una o más líneas en blanco
            import re as _re
            trozos = _re.split(r"\n\s*\n", texto)

            for trozo in trozos:
                lineas = trozo.splitlines()
                if not lineas:
                    continue
                primera = lineas[0].strip()

                # --- Encabezados ---
                enc = _re.match(r"^(#{1,6})\s+(.*)$", primera)
                if enc and len(lineas) == 1:
                    nivel = len(enc.group(1))
                    titulo_html = markdown.markdown(
                        enc.group(2).strip()
                    ).strip()
                    # Elimina el <p> envolvente que añade markdown
                    titulo_html = (
                        titulo_html.replace("<p>", "")
                        .replace("</p>", "")
                    )
                    if nivel == 1:
                        bloques.append(("h1", titulo_html))
                    elif nivel == 2:
                        bloques.append(("h2i", titulo_html))
                    else:  # nivel 3+
                        bloques.append(("h3", titulo_html))
                    continue

                # --- Listas (bloque que empieza con -, * o 1.) ---
                if _re.match(r"^\s*([-*+]|\d+\.)\s+", primera):
                    html = markdown.markdown(trozo, extensions=["extra"])
                    # Convierte <li> en viñetas con salto de línea
                    html = html.replace("<ul>", "")
                    html = html.replace("</ul>", "")
                    html = html.replace("<ol>", "")
                    html = html.replace("</ol>", "")
                    html = html.replace("<li>", "\u2022&nbsp; ")
                    html = html.replace("</li>", "<br/>")
                    # Cada <p> interno se limpia (el Paragraph da el estilo)
                    html = html.replace("<p>", "").replace("</p>", "")
                    bloques.append(("lista", html))
                    continue

                # --- Párrafo normal ---
                html = markdown.markdown(trozo, extensions=["extra"])
                html = html.replace("<p>", "").replace("</p>", "")
                bloques.append(("parr", html))

            return bloques

        # Funciones de renderizado por tipo de bloque
        def render_bbloque(tipo, html):
            if tipo == "h1":
                return Paragraph(html or "&nbsp;", estilos["h1"])
            if tipo == "h2i":
                return Paragraph(html or "&nbsp;", estilos["h2i"])
            if tipo == "h3":
                return Paragraph(html or "&nbsp;", estilos["h3"])
            if tipo == "lista":
                return Paragraph(html or "&nbsp;", estilos["lista"])
            return Paragraph(html or "&nbsp;", estilos["cuerpo"])

        doc = SimpleDocTemplate(
            ruta, pagesize=A4,
            rightMargin=20 * mm, leftMargin=20 * mm,
            topMargin=18 * mm, bottomMargin=18 * mm,
        )

        historia = []
        historia.append(Paragraph(
            _escape_html(nombre_capitulo), estilos["titulo"]
        ))
        historia.append(Paragraph(
            _escape_html(f"Libro: {nombre_libro}"), estilos["libro"]
        ))
        historia.append(HRFlowable(
            width="100%", thickness=1, color=colors.HexColor("#c9c9c9")
        ))

        secciones = [
            ("Resumen", ch.sectors.get("resumen", "")),
            ("Datos importantes", ch.sectors.get("datos_importantes", "")),
            ("Glosario", ch.sectors.get("glosario", "")),
            ("Cuerpo", ch.transcribed_text),
        ]
        for titulo, contenido in secciones:
            historia.append(Paragraph(_escape_html(titulo), estilos["h2"]))
            for tipo, html in md_a_bloques(contenido):
                historia.append(render_bbloque(tipo, html))

        doc.build(historia)
        self.chapter_view.set_status(f"✓ Exportado: {nombre_seguro}.pdf")

    # ==================================================================
    # Cierre
    # ==================================================================
    def on_close(self):
        try:
            self.recorder.stop()
        except Exception:
            pass
        self.destroy()


def main():
    app = DictonotoApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()
