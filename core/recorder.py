"""Grabador de audio en tiempo real usando sounddevice.

Captura audio del micrófono a 16 kHz (mono) y lo acumula en un buffer
global (para la transcripción completa) y en un buffer de "frase" para
la transcripción en vivo.

La transcripción en vivo dispara un fragmento de dos formas:

1. **Pausa de silencio**: tras ``silence_pause_seconds`` segundos sin voz
   se considera la frase terminada y se envía a transcribir.
2. **Longitud máxima (streaming)**: si la frase supera
   ``max_fragment_seconds`` (aunque no haya silencio), se envía un
   fragmento parcial para mantener el texto fresco en la hoja lateral.

Ambos mecanismos hacen que la transcripción se sienta "en tiempo real".
"""
import threading

import numpy as np
import sounddevice as sd

SAMPLE_RATE = 16000  # faster-whisper espera 16 kHz
SILENCE_THRESHOLD = 0.012  # RMS por debajo del cual se considera silencio
DEFAULT_MAX_FRAGMENT_SECONDS = 12.0  # streaming: fragmento máximo antes de silencio


class AudioRecorder:
    """Graba audio continuamente y notifica fragmentos de voz."""

    def __init__(self, samplerate=SAMPLE_RATE, channels=1, input_device=None):
        self.samplerate = samplerate
        self.channels = channels
        self.input_device = input_device  # None => dispositivo por defecto
        self.stream = None

        # Configuración de pausa (actualizada por la app)
        self.silence_pause_seconds = 6.0
        self.max_fragment_seconds = DEFAULT_MAX_FRAGMENT_SECONDS
        self.auto_quick_transcription = True

        # Buffers
        self.all_audio = np.zeros(0, dtype="float32")  # todo el audio
        self.sentence_audio = np.zeros(0, dtype="float32")  # frase actual
        self._lock = threading.Lock()
        self._silence_seconds = 0.0

        # Callbacks
        self.on_quick_fragment = None  # callable(fragment_np) - transcripción en vivo
        # callable(nivel: float 0.0-1.0) para el medidor de sonido en vivo
        self.on_volume_level = None

    # ------------------------------------------------------------------
    def start(self):
        """Comienza a capturar audio del micrófono."""
        self.all_audio = np.zeros(0, dtype="float32")
        self.sentence_audio = np.zeros(0, dtype="float32")
        self._silence_seconds = 0.0

        def callback(indata, frames, time_info, status):
            audio = indata[:, 0].copy()  # mono
            self._process(audio)

        self.stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            dtype="float32",
            callback=callback,
            blocksize=int(self.samplerate * 0.1),  # bloques de 100 ms
            device=self.input_device,
        )
        self.stream.start()

    # ------------------------------------------------------------------
    def _es_fragmento_emisible(self) -> bool:
        """True si la frase acumulada ya es lo bastante larga para transcribir."""
        return len(self.sentence_audio) >= self.samplerate

    def _procesar_nivel(self, rms: float):
        """Convierte el RMS en un nivel 0-1 y notifica al medidor (si existe).

        Usa una escala semilogarítmica (parecida a dB) para que sea visual:
        el silencio (~0) cae a 0 y el ruido fuerte (~0.3+) se satura a 1.
        """
        if self.on_volume_level is None:
            return
        # Normalización perceptual: nivel en dBFS relativo a 1.0
        if rms <= 0:
            nivel = 0.0
        else:
            try:
                import math
                db = 20.0 * math.log10(rms)  # dBFS (0 dB = señal completa)
                # Mapea aproximadamente de -50 dB a 0 dB -> 0.0 a 1.0
                nivel = max(0.0, min(1.0, (db + 50.0) / 50.0))
            except (ValueError, OverflowError):
                nivel = 0.0
        self.on_volume_level(nivel)

    def _process(self, audio: np.ndarray):
        """Analiza cada bloque: acumula audio y detecta pausas/fragmentos."""
        rms = float(np.sqrt(np.mean(audio ** 2))) if audio.size else 0.0

        # Notifica el nivel para el medidor de sonido en vivo
        self._procesar_nivel(rms)

        with self._lock:
            self.all_audio = np.concatenate([self.all_audio, audio])

            if self.auto_quick_transcription:
                # Acumulamos la frase actual (voz y silencio para no cortar cola)
                self.sentence_audio = np.concatenate(
                    [self.sentence_audio, audio]
                )

                if rms > SILENCE_THRESHOLD:
                    # Hay voz: reset del contador de silencio
                    self._silence_seconds = 0.0
                else:
                    self._silence_seconds += len(audio) / self.samplerate

                # 1) Pausa larga: se cierra el bloque (voz ya acumulada)
                pausa_larga = (
                    self._silence_seconds >= self.silence_pause_seconds
                    and self._es_fragmento_emisible()
                )
                # 2) Streaming: fragmento demasiado largo sin pausa
                longitud_max = (
                    len(self.sentence_audio)
                    >= self.samplerate * self.max_fragment_seconds
                )

                if pausa_larga or longitud_max:
                    fragmento = self.sentence_audio
                    self.sentence_audio = np.zeros(0, dtype="float32")
                    self._silence_seconds = 0.0
                    # Transcripción en vivo: se dispara siempre (pausa o
                    # streaming) para mantener el texto bruto al día.
                    if self.on_quick_fragment:
                        self.on_quick_fragment(fragmento)
            else:
                # Transcripción rápida desactivada: no acumulamos frases
                self.sentence_audio = np.zeros(0, dtype="float32")

    # ------------------------------------------------------------------
    def stop(self) -> np.ndarray:
        """Detiene la grabación y devuelve todo el audio capturado (16 kHz)."""
        # Guarda el fragmento de frase restante para no perder lo último
        # que se dijo antes de detener.
        with self._lock:
            self._residual_fragment = self.sentence_audio.copy()
            resultado = self.all_audio.copy()
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            finally:
                self.stream = None
        return resultado

    def pop_residual_fragment(self) -> np.ndarray:
        """Devuelve el audio de frase que quedó sin transcribir al detener.

        Permite procesar el último tramo hablado (sin esperar una pausa)
        al terminar la grabación, evitando perder contenido. Devuelve un
        array vacío si no había nada pendiente.
        """
        with self._lock:
            frag = getattr(self, "_residual_fragment", None)
            self._residual_fragment = np.zeros(0, dtype="float32")
            return frag if frag is not None else np.zeros(0, dtype="float32")


def listar_dispositivos_entrada() -> list:
    """Devuelve los dispositivos de entrada (micrófonos) disponibles.

    Cada elemento es una tupla ``(nombre_legible, índice_dispositivo)``.
    El índice se pasa directamente a ``sounddevice.InputStream(device=...)``.
    """
    try:
        dispositivos = sd.query_devices()
    except Exception:
        return []
    resultado = []
    for i, dev in enumerate(dispositivos):
        # 'max_input_channels > 0' indica que es una entrada capturable
        if dev.get("max_input_channels", 0) > 0:
            nombre = dev.get("name", f"Dispositivo {i}")
            resultado.append((f"{nombre}", i))
    return resultado
