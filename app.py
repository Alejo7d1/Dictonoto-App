"""Controlador principal de Dictonoto.

Orquesta la biblioteca, los libros/capítulos, la grabación de audio, la
transcripción (rápida y completa) y la IA. Es el puente entre la UI y
las capas de servicio.
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
        self.recorder.on_sentence_complete = self._on_sentence_complete
        self.recorder.on_volume_level = self._on_volume_level

        # Estado de navegación
        self.current_book: Book | None = None
        self.current_chapter = None
        self.chapter_view: ChapterView | None = None

        # Marca de hasta dónde se ha enviado texto bruto a la IA, para
        # que cada bloque (desde la última pausa larga) se procese una vez.
        self._ai_marker = 0

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
        self._ai_marker = 0  # nueva marca de hasta dónde se formateó con IA
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
                # Primer transcribe el tramo residual (en vivo)…
                self._enqueue_work(self._transcibe_rapida, residual)
            else:
                # Sin audio residual relevante.
                self.after(0, lambda: self.chapter_view.set_status(
                    "✓ Grabación detenida"
                ))
            # …y después formatea con IA el bloque pendiente (si lo hay).
            self._enqueue_work(self._formatear_bloque_ia)
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
        alimenta el texto bruto en vivo. La IA se invoca aparte cuando se
        cierra un bloque por pausa larga (ver _on_sentence_complete).
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

    def _on_sentence_complete(self, pendiente: bool = True):
        """Pausa larga: encola el formateo con IA del bloque bruto pendiente."""
        self._enqueue_work(self._formatear_bloque_ia)

    def _formatear_bloque_ia(self):
        """Formatea con la IA el bloque bruto nuevo (desde la última pausa).

        Se envía únicamente el tramo de texto bruto acumulado desde la
        última vez que se formateó con IA (marcado por self._ai_marker),
        de modo que cada bloque pausa a pausa se procese una sola vez.
        """
        if self.current_chapter is None:
            return
        if not self.config.get("ai", "api_key"):
            # Sin IA configurada: nada que formatear (se conserva el bruto).
            return

        bruto = self.current_chapter.raw_text
        bloque = bruto[self._ai_marker:].strip()
        if not bloque:
            return

        try:
            self.ai.quick_transcription(self.current_chapter, bloque)
            # Avanza la marca: este bloque ya se formateó
            self._ai_marker = len(bruto)
            self.after(0, self._refresh_chapter_ui_after_quick)
        except Exception as e:
            # Si la IA falla, conservamos el texto bruto.
            self.after(0, lambda e=e: self._mostrar_error(str(e)))

    def _refresh_raw_ui(self):
        if self.chapter_view:
            self.chapter_view.sync_after_recording()

    def _refresh_chapter_text_ui(self):
        if self.chapter_view:
            self.chapter_view.transcribed_box.configure(state="normal")
            self.chapter_view.transcribed_box.delete("1.0", "end")
            self.chapter_view.transcribed_box.insert(
                "1.0", self.current_chapter.transcribed_text
            )
            self.chapter_view.transcribed_box.configure(state="normal")

    def _refresh_chapter_ui_after_quick(self):
        if self.chapter_view:
            self.chapter_view.transcribed_box.delete("1.0", "end")
            self.chapter_view.transcribed_box.insert(
                "1.0", self.current_chapter.transcribed_text
            )
            self.chapter_view.sync_sections()
            self.chapter_view.set_status("• Se actualizó el cuerpo")

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
            self.chapter_view.transcribed_box.delete("1.0", "end")
            self.chapter_view.transcribed_box.insert(
                "1.0", self.current_chapter.transcribed_text
            )
            self.chapter_view.sync_sections()
            self.chapter_view.set_status("✓ Transcripción completa lista")

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
