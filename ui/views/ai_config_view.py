"""Vista de configuración de la IA (página inline, no diálogo).

Permite configurar el enlace (base URL), el modelo, la API key, la
temperatura, el prompt de sistema, el tiempo de pausa de silencio y el
modelo Whisper local. Todo se guarda en ``settings.json``.

Los diálogos modales quedan reservados únicamente para alertas.
"""
import customtkinter as ctk

from config.config_manager import ConfigManager
from core.ai_service import AIService
from core.recorder import listar_dispositivos_entrada

# Paleta
BG = "#121212"
PANEL = "#1e1e1e"
PANEL2 = "#2a2a2a"
ACCENTO = "#6c5ce7"
TEXTO = "#e8e8e8"
SUBTEXTO = "#9a9a9a"


class AIConfigView(ctk.CTkFrame):
    """Página de ajustes del modelo de IA y de la transcripción."""

    def __init__(self, master, config: ConfigManager, on_saved=None, on_back=None):
        super().__init__(master, fg_color=BG)
        self.config = config
        self.on_saved = on_saved
        self.on_back = on_back

        self._build()

    # ------------------------------------------------------------------
    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Cabecera
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 4))
        ctk.CTkButton(
            header, text="‹ Volver", width=80,
            fg_color="transparent", hover_color=PANEL2,
            text_color=TEXTO, command=self._back,
        ).pack(side="left")
        ctk.CTkLabel(
            header, text="Configuración",
            font=ctk.CTkFont(size=20, weight="bold"), text_color=TEXTO,
        ).pack(side="left", padx=12)

        # Cuerpo (scroll)
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew", padx=20, pady=(4, 8))
        scroll.grid_columnconfigure(0, weight=1)

        # Contador de filas: avanza con cada elemento añadido. Al usar el
        # mismo `scroll` como padre, todas las filas quedan consecutivas y
        # sin solapamientos.
        fila = 0

        # ================= Sección IA =================
        fila = self._titulo_seccion(
            scroll, fila, "IA (formateo de texto)",
            "Compatible con la API de OpenAI (DeepSeek, Kimi…)",
        )
        fila = self._campo(
            scroll, fila, "Enlace (Base URL)", "ai", "base_url",
            placeholder="https://api.deepseek.com",
        )
        fila = self._campo(
            scroll, fila, "Modelo", "ai", "model",
            placeholder="deepseek-v4-flash",
        )
        fila = self._campo(
            scroll, fila, "API Key", "ai", "api_key",
            show="•", placeholder="sk-...",
        )
        fila = self._campo(
            scroll, fila, "Temperatura (0.0 - 2.0)", "ai", "temperature",
            placeholder="0.3",
        )

        # ================= Sección grabación / transcripción =================
        fila = self._titulo_seccion(
            scroll, fila, "Transcripción y audio",
            "Funciona sin conexión; la IA solo se usa para formatear.",
        )

        # Selector de dispositivo de entrada (micrófono)
        dispositivos, self._device_index = self._cargar_dispositivos()
        fila = self._selector_dispositivo(
            scroll, fila, "Entrada de audio (micrófono)", dispositivos,
        )

        self.auto_var = ctk.BooleanVar(
            value=bool(self.config.get("recording", "auto_quick_transcription", True))
        )
        fila = self._switch(
            scroll, fila,
            "Transcripción en vivo al detectar pausa / fragmento",
            self.auto_var,
        )
        fila = self._campo(
            scroll, fila,
            "Pausa de silencio (segundos) para cerrar frase",
            "recording", "silence_pause_seconds", placeholder="8",
        )
        fila = self._campo(
            scroll, fila,
            "Máx. duración de fragmento en vivo (segundos)",
            "recording", "max_fragment_seconds", placeholder="12",
        )
        # Selector de dispositivo Whisper (GPU / CPU)
        fila = self._selector_opcion(
            scroll, fila, "Dispositivo Whisper",
            "recording", "device",
            ["auto", "cuda", "cpu"],
            "auto",
        )
        # Modelo Whisper como lista desplegable
        fila = self._selector_lista(
            scroll, fila, "Modelo Whisper",
            "recording", "whisper_model",
            ["tiny", "base", "small", "medium", "large"],
            "small",
        )

        # ================= Prompt de sistema =================
        fila = self._titulo_seccion(scroll, fila, "Prompt de sistema (avanzado)", "")
        self.prompt_box = ctk.CTkTextbox(
            scroll, height=120, fg_color=PANEL, text_color=TEXTO,
            border_width=1, border_color=PANEL2,
            font=ctk.CTkFont(size=12), wrap="word",
        )
        self.prompt_box.grid(row=fila, column=0, sticky="ew", pady=(0, 10))
        fila += 1
        self.prompt_box.insert(
            "1.0",
            self.config.get("ai", "system_prompt", ""),
        )

        # ================= Barra inferior fija (siempre visible) =================
        barra_fija = ctk.CTkFrame(self, fg_color="transparent")
        barra_fija.grid(row=2, column=0, sticky="ew", padx=20, pady=(4, 10))

        self.estado = ctk.CTkLabel(
            barra_fija, text="", font=ctk.CTkFont(size=11), text_color=SUBTEXTO
        )
        self.estado.pack(side="left", padx=6)

        ctk.CTkButton(
            barra_fija, text="Probar conexión", width=140,
            fg_color=PANEL2, hover_color="#3a3a3a", text_color=TEXTO,
            command=self._test,
        ).pack(side="right", padx=6)
        ctk.CTkButton(
            barra_fija, text="Cancelar", width=100,
            fg_color="transparent", hover_color=PANEL2, text_color=SUBTEXTO,
            command=self._back,
        ).pack(side="right", padx=6)
        ctk.CTkButton(
            barra_fija, text="Guardar", width=140,
            fg_color=ACCENTO, hover_color="#5a4bd1", text_color="white",
            command=self._guardar,
        ).pack(side="right", padx=6)

    # ------------------------------------------------------------------
    # Helpers de construcción del grid (fila incremental)
    # ------------------------------------------------------------------
    def _titulo_seccion(self, parent, fila, titulo, subtexto) -> int:
        """Añade el título de una sección y (opcional) un subtítulo."""
        ctk.CTkLabel(
            parent, text=titulo,
            font=ctk.CTkFont(size=15, weight="bold"), text_color=TEXTO,
        ).grid(row=fila, column=0, sticky="w", pady=(18, 2))
        fila += 1
        if subtexto:
            ctk.CTkLabel(
                parent, text=subtexto,
                font=ctk.CTkFont(size=12), text_color=SUBTEXTO,
            ).grid(row=fila, column=0, sticky="w", pady=(0, 8))
            fila += 1
        return fila

    def _campo(self, parent, fila, etiqueta, categoria, clave,
               placeholder="", show=None) -> int:
        """Añade un label + entry y devuelve la siguiente fila libre."""
        ctk.CTkLabel(
            parent, text=etiqueta,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXTO, anchor="w",
        ).grid(row=fila, column=0, sticky="ew", pady=(8, 2))
        fila += 1

        entry = ctk.CTkEntry(
            parent, fg_color=PANEL, text_color=TEXTO,
            border_width=1, border_color=PANEL2,
            show=show or None, placeholder_text=placeholder,
        )
        entry.insert(0, str(self.config.get(categoria, clave, "") or ""))
        entry.grid(row=fila, column=0, sticky="ew", pady=(0, 2))
        fila += 1
        setattr(self, f"_entry_{clave}", entry)
        return fila

    def _switch(self, parent, fila, texto, variable) -> int:
        ctk.CTkSwitch(
            parent, text=texto, variable=variable, text_color=TEXTO,
            progress_color=ACCENTO, button_color=PANEL2,
            font=ctk.CTkFont(size=13),
        ).grid(row=fila, column=0, sticky="w", pady=(10, 2))
        return fila + 1

    def _selector_lista(self, parent, fila, etiqueta, categoria, clave,
                        opciones, por_defecto) -> int:
        """Desplegable para un valor de configuración con opciones fijas."""
        ctk.CTkLabel(
            parent, text=etiqueta,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXTO, anchor="w",
        ).grid(row=fila, column=0, sticky="ew", pady=(8, 2))
        fila += 1

        actual = str(self.config.get(categoria, clave, por_defecto) or por_defecto)
        var = ctk.StringVar(value=actual if actual in opciones else por_defecto)
        ctk.CTkOptionMenu(
            parent, values=opciones, variable=var, fg_color=PANEL,
            text_color=TEXTO, button_color=PANEL2, button_hover_color="#3a3a3a",
            dropdown_fg_color=PANEL2, dropdown_text_color=TEXTO,
            dropdown_hover_color="#3a3a3a", width=200,
        ).grid(row=fila, column=0, sticky="w", pady=(0, 2))
        fila += 1
        # Almacena la variable para poder leerla en _valores()
        setattr(self, f"_option_{clave}", var)
        return fila

    def _selector_opcion(self, parent, fila, etiqueta, categoria, clave,
                         opciones, por_defecto) -> int:
        """Alias de _selector_lista para opciones de dispositivo (GPU/CPU)."""
        return self._selector_lista(
            parent, fila, etiqueta, categoria, clave, opciones, por_defecto
        )

    def _selector_dispositivo(self, parent, fila, etiqueta, dispositivos) -> int:
        """Añade un desplegable con los micrófonos disponibles."""
        ctk.CTkLabel(
            parent, text=etiqueta,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=TEXTO, anchor="w",
        ).grid(row=fila, column=0, sticky="ew", pady=(8, 2))
        fila += 1

        # Mapas: nombre legible -> índice real del dispositivo
        self._device_nombres = [nombre for nombre, _idx in dispositivos]
        self._device_indices = [idx for _nombre, idx in dispositivos]
        self._device_var = ctk.StringVar(
            value=self._device_nombres[self._device_index]
            if self._device_nombres else ""
        )
        ctk.CTkOptionMenu(
            parent, values=self._device_nombres or ["(sin dispositivos)"],
            variable=self._device_var, fg_color=PANEL, text_color=TEXTO,
            button_color=PANEL2, button_hover_color="#3a3a3a",
            dropdown_fg_color=PANEL2, dropdown_text_color=TEXTO,
            dropdown_hover_color="#3a3a3a", width=200,
        ).grid(row=fila, column=0, sticky="w", pady=(0, 2))
        fila += 1
        return fila

    def _cargar_dispositivos(self):
        """Carga los micrófonos; devuelve (lista, índice_guardado)."""
        try:
            dispositivos = listar_dispositivos_entrada()
        except Exception:
            dispositivos = []
        guardado = self.config.get("recording", "input_device", None)
        indice = 0
        for i, (nombre, idx) in enumerate(dispositivos):
            if str(idx) == str(guardado):
                indice = i
                break
        return dispositivos, indice

    # ------------------------------------------------------------------
    def _valores(self) -> dict:
        def leer(clave):
            return getattr(self, f"_entry_{clave}").get()

        # Dispositivo seleccionado (índice real de sounddevice o None)
        dispositivo_sel = None
        if self._device_indices:
            try:
                indice_nombre = self._device_nombres.index(self._device_var.get())
                dispositivo_sel = self._device_indices[indice_nombre]
            except (ValueError, IndexError):
                dispositivo_sel = None

        return {
            "ai": {
                "base_url": leer("base_url").strip(),
                "model": leer("model").strip(),
                "api_key": leer("api_key").strip(),
                "temperature": self._float(leer("temperature"), 0.3),
                "system_prompt": self.prompt_box.get("1.0", "end").strip(),
            },
            "recording": {
                "silence_pause_seconds": self._float(
                    leer("silence_pause_seconds"),
                    self.config.get("recording", "silence_pause_seconds", 8),
                ),
                "max_fragment_seconds": self._float(
                    leer("max_fragment_seconds"),
                    self.config.get("recording", "max_fragment_seconds", 12),
                ),
                "auto_quick_transcription": bool(self.auto_var.get()),
                "whisper_model": self._option_whisper_model.get(),
                "device": self._option_device.get(),
                "input_device": dispositivo_sel,
            },
        }

    def _float(self, valor, por_defecto=0.3):
        try:
            return float(valor)
        except (TypeError, ValueError):
            return por_defecto

    # ------------------------------------------------------------------
    def _back(self):
        if self.on_back:
            self.on_back()

    def _guardar(self):
        self.config.save_config(self._valores())
        if self.on_saved:
            self.on_saved()
        else:
            self._back()

    def _test(self):
        self.estado.configure(text="Probando conexión…", text_color="orange")
        self.update_idletasks()
        try:
            # Guarda temporalmente y prueba
            self.config.save_config(self._valores())
            service = AIService(self.config)
            ok = service.test_connection()
            self.estado.configure(
                text="✅ Conexión exitosa" if ok else "⚠️ Respuesta inesperada",
                text_color="#2ecc71" if ok else "#e67e22",
            )
        except Exception as e:
            self.estado.configure(
                text=f"❌ Error: {e}", text_color="#e74c3c"
            )
