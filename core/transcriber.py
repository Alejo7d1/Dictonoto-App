"""Transcriptor de audio a texto usando faster-whisper (100 % local).

Ejecuta el modelo Whisper local para convertir fragmentos de audio
(16 kHz, mono, float32) en texto. Todo el reconocimiento ocurre en esta
máquina; la nube solo se usa para el formateo (ver core/ai_service.py).

La UI orquesta un hilo de trabajo para que el reconocimiento no bloquee
la interfaz.
"""
import os

# Suprime avisos molestos de Hugging Face Hub antes de importar la librería:
# - HF_HUB_DISABLE_SYMLINKS_WARNING: evita avisar de no usar symlinks en
#   Windows (la caché funciona igual, solo ocupa un poco más de disco).
# - El aviso de "unauthenticated requests" es informativo y no afecta al
#   uso local; lo silenciamos vía logging de huggingface_hub.
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

import logging
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)


def _configurar_rutas_cuda():
    """Registra las DLLs de CUDA de NVIDIA para que Windows las encuentre."""
    if os.name != "nt":
        return  # En Linux/macOS el loader encuentra las .so automáticamente

    import pathlib
    import site
    import sys
    import sysconfig

    # Recopilar rutas potenciales de site-packages (globales y de venv)
    rutas_site = set(site.getsitepackages())
    rutas_site.add(sysconfig.get_path("purelib"))
    rutas_site.add(sysconfig.get_path("platlib"))
    rutas_site.add(str(pathlib.Path(sys.prefix) / "Lib" / "site-packages"))

    registradas = set()
    for raiz in rutas_site:
        base = pathlib.Path(raiz) / "nvidia"
        if not base.is_dir():
            continue
        for carpeta in base.glob("*"):
            for sub in ("bin", "lib"):
                dll_dir = carpeta / sub
                if dll_dir.is_dir():
                    try:
                        os.add_dll_directory(str(dll_dir))
                        # También añadimos al PATH por compatibilidad con subprocesos C++
                        os.environ["PATH"] = str(dll_dir) + os.pathsep + os.environ.get("PATH", "")
                        registradas.add(str(dll_dir))
                    except (OSError, ValueError):
                        pass

    if registradas:
        print("[Whisper] Directorios CUDA de NVIDIA registrados exitosamente:")
        for ruta in sorted(registradas):
            print(f"  - {ruta}")

_configurar_rutas_cuda()

import numpy as np
from faster_whisper import WhisperModel


class Transcriber:
    """Envuelve un modelo faster-whisper y transcribe arrays de audio.

    Soporta usar GPU (CUDA/RTX) o CPU. Con ``device="auto"`` se intenta
    usar la GPU si está disponible (y las librerías CUDA están instaladas)
    y, si no, se cae a CPU automáticamente sin errores.
    """

    def __init__(self, model_size: str = "small", device: str = "auto"):
        self.model_size = model_size
        self.device = device            # "auto" | "cuda" | "cpu"
        self.model = None
        self.used_device = None         # dispositivo que terminó usándose
        self.used_compute_type = None

    # ------------------------------------------------------------------
    def ensure_loaded(self):
        """Carga el modelo Whisper en memoria (una sola vez, local).

        Intenta el dispositivo configurado (auto/cuda) y, ante cualquier
        fallo (p. ej. falta de librerías CUDA como cublas64_12.dll), cae
        automáticamente a CPU para que la transcripción siempre funcione.
        """
        if self.model is None:
            self.model = self._load()
            if self.model is None:
                raise RuntimeError(
                    "No se pudo cargar el modelo Whisper en ningún "
                    "dispositivo (GPU ni CPU)."
                )

    def _load(self):
        """Carga el modelo. Devuelve None si falla en todos los dispositivos."""
        for dispositivo, compute in self._dispositivos_candidatos():
            try:
                modelo = WhisperModel(
                    self.model_size,
                    device=dispositivo,
                    compute_type=compute,
                )
                self.used_device = dispositivo
                self.used_compute_type = compute
                print(
                    f"[Whisper] modelo '{self.model_size}' en "
                    f"{dispositivo} ({compute})"
                )
                return modelo
            except Exception:
                # Intenta el siguiente candidato
                continue
        return None

    def _dispositivos_candidatos(self) -> list:
        """Devuelve [(dispositivo, compute_type), ...] en orden de preferencia.

        - "auto": intenta GPU (float16, rápido en RTX) y, si no hay tarjeta
          NVIDIA compatible, usa CPU (int8).
        - "cuda": SOLO GPU. Si CUDA falla, el error se propaga (nada de
          degradar a CPU en silencio).
        - "cpu": solo CPU (int8).
        """
        preferencia = str(self.device).lower()

        if preferencia in ("auto", ""):
            return [("cuda", "float16"), ("cpu", "int8")]
        if preferencia == "cuda":
            return [("cuda", "float16")]
        return [("cpu", "int8")]

    def change_model(self, model_size: str):
        """Cambia el tamaño del modelo Whisper y lo recarga."""
        self.model_size = model_size
        self.model = None

    def reset_context(self):
        """Olvida el contexto anterior (p. ej. al abrir otro capítulo)."""
        self.previous_text = ""

    # ------------------------------------------------------------------
    def transcribe(self, audio: np.ndarray) -> str:
        """Transcribe un array de audio a texto (devuelve el texto).

        Cada fragmento se transcribe de forma *independiente* (sin
        contexto previo) para evitar duplicaciones. Si falla, el error
        se propaga tal cual (gracias a _configurar_rutas_cuda ya no debe
        fallar CUDA con 'cublas64_12.dll' al procesar audio).
        """
        if audio is None or len(audio) == 0:
            return ""
        self.ensure_loaded()

        segments, _info = self.model.transcribe(
            audio,
            beam_size=1,       # respuesta rápida (transcripción en vivo)
            language="es",
            vad_filter=True,
        )

        return " ".join(seg.text.strip() for seg in segments).strip()
