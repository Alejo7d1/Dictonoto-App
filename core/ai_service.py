"""Servicio de IA (LLM) para Dictonoto.

Conecta con cualquier API compatible con OpenAI (configurable mediante
enlace, modelo, api-key y temperatura). Ofrece dos orquestaciones de
transcripción:

- ``quick_transcription``: texto de "transcripción rápida" (un fragmento
  corto tras una pausa). Actualiza el sector "cuerpo" del capítulo.
- ``full_transcription``: toma el texto bruto completo y lo reorganiza en
  los sectores (resumen, datos importantes, glosario y cuerpo).

Todos los ajustes (enlace, modelo, api-key, temperatura, prompt) se
obtienen desde el ``ConfigManager`` (archivo ``settings.json``).
"""
import re
from openai import OpenAI

from config.config_manager import ConfigManager
from models.chapter import Chapter


class AIService:
    """Encapsula la comunicación con la API de un modelo LLM."""

    def __init__(self, config: ConfigManager | None = None):
        self.config = config or ConfigManager()

    # ------------------------------------------------------------------
    # Configuración de la API
    # ------------------------------------------------------------------
    def _client(self) -> OpenAI:
        """Crea un cliente OpenAI apuntando a la URL/API key configuradas."""
        base_url = self.config.get("ai", "base_url", "")
        api_key = self.config.get("ai", "api_key", "")
        if not base_url or not api_key:
            raise ValueError(
                "La IA no está configurada. Abre Ajustes de IA y añade "
                "el enlace, modelo y API key."
            )
        return OpenAI(base_url=base_url, api_key=api_key)

    def _temperature(self) -> float:
        try:
            return float(self.config.get("ai", "temperature", 0.3))
        except (TypeError, ValueError):
            return 0.3

    def _system_prompt(self) -> str:
        return self.config.get(
            "ai",
            "system_prompt",
            DEFAULT_SYSTEM_PROMPT,
        )

    # ------------------------------------------------------------------
    # Llamada base a la API
    # ------------------------------------------------------------------
    def _chat(self, system: str, user: str) -> str:
        """Ejecuta un chat de una sola pasada y devuelve el texto resultante."""
        client = self._client()
        model = self.config.get("ai", "model", "")
        if not model:
            raise ValueError("No se ha especificado un modelo de IA.")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=self._temperature(),
        )
        return (response.choices[0].message.content or "").strip()

    # ------------------------------------------------------------------
    # Verificación de conexión / clave
    # ------------------------------------------------------------------
    def test_connection(self) -> bool:
        """Envía un mensaje trivial para comprobar que la API responde."""
        result = self._chat(
            system="Responde únicamente con la palabra OK.",
            user="Prueba de conexión.",
        )
        return "OK" in result.upper()

    # ------------------------------------------------------------------
    # Transcripción rápida (bloque tras una pausa larga)
    # ------------------------------------------------------------------
    def quick_transcription(self, chapter: Chapter, fragment: str) -> str:
        """Formatea un bloque de texto bruto y lo añade al 'cuerpo'.

        La IA recibe SOLO el bloque nuevo (desde la última pausa) y debe
        devolver SOLO su versión limpia, sin repetir el cuerpo existente.
        Esto evita el acoplamiento exponencial de pasarle todo acumulado.

        Devuelve el nuevo texto del sector 'cuerpo' ya incrementado.
        """
        system = (
            f"{self._system_prompt()}\n\n"
            "Tarea: Recibes un BLOQUE de una transcripción de clase, en "
            "texto bruto (con posibles errores del reconocimiento de voz). "
            "Devuelve ÚNICAMENTE una versión limpia y formateada en "
            "Markdown de ese bloque.\n\n"
            "REGLAS:\n"
            "- Conserva el orden de las ideas tal como aparecen.\n"
            "- NO inventes ni repitas contenido que no venga en el bloque.\n"
            "- NO escribas encabezados de sección ni el texto de bloques "
            "anteriores.\n"
            "- Devuelve solo el texto, sin comentarios ni explicaciones."
        )
        user = f"Bloque a formatear:\n```\n{fragment}\n```"
        fragmento_formateado = self._chat(system, user)

        # Acumular de forma segura (evita sobrescribir y evita duplicar)
        chapter.sectors["cuerpo"] = (
            self._merge_body(chapter.sectors["cuerpo"], fragmento_formateado)
        )
        chapter.transcribed_text = self._render_body(chapter)
        return chapter.sectors["cuerpo"]

    def _merge_body(self, actual: str, nuevo: str) -> str:
        """Une el cuerpo existente y el fragmento formateado por la IA.

        Pese a que el prompt pide devolver solo el fragmento, algunos
        modelos repiten el cuerpo anterior. Aquí se recorta cualquier
        repetición del cuerpo previo que aparezca al inicio del texto
        nuevo, para no duplicar contenido.
        """
        actual_l = actual.strip()
        nuevo_l = nuevo.strip()
        if not actual_l:
            return nuevo_l
        if not nuevo_l:
            return actual_l

        # Si el texto nuevo ya está íntegramente contenido en el cuerpo
        # actual, no hay nada que añadir.
        if nuevo_l in actual_l:
            return actual_l

        # Recorta el cuerpo previo si el modelo lo repitió al inicio.
        # Se prueba el cuerpo completo y, si no, un prefijo suficientemente
        # largo del cuerpo actual (evita recortes parciales de frases).
        trozos = []
        if nuevo_l.startswith(actual_l):
            nuevo_l = nuevo_l[len(actual_l):].strip()
            if not nuevo_l:
                return actual_l
            trozos = [nuevo_l]
        else:
            # El modelo suele repetir los primeros caracteres del cuerpo.
            # Extraemos el prefijo más largo del cuerpo actual que coincida
            # al inicio de 'nuevo', con un mínimo de 30 caracteres para no
            # recortar frases a la ligera.
            recorte = ""
            limite = min(len(actual_l), 200)
            for largo in range(limite, 29, -1):
                if nuevo_l.startswith(actual_l[:largo]):
                    recorte = actual_l[:largo]
                    break
            if recorte:
                resto = nuevo_l[len(recorte):].strip()
                if resto:
                    trozos = [resto]
                else:
                    return actual_l
            else:
                trozos = [nuevo_l]

        return f"{actual_l}\n\n{'\n\n'.join(t for t in trozos if t)}"

    def _render_body(self, chapter: Chapter) -> str:
        """Reconstruye el texto transcrito a partir de los sectores."""
        partes = []
        for clave, etiqueta in (
            ("resumen", "## Resumen"),
            ("datos_importantes", "## Datos importantes"),
            ("glosario", "## Glosario"),
            ("cuerpo", "## Cuerpo"),
        ):
            contenido = chapter.sectors.get(clave, "").strip()
            if contenido:
                partes.append(f"{etiqueta}\n\n{contenido}")
        return "\n\n".join(partes)

    # ------------------------------------------------------------------
    # Transcripción completa (reorganiza toda la nota original)
    # ------------------------------------------------------------------
    def full_transcription(self, chapter: Chapter) -> dict:
        """Reorganiza el texto bruto completo en los 4 sectores.

        Devuelve el diccionario de sectores actualizado.
        """
        system = (
            f"{self._system_prompt()}\n\n"
            "Tarea de ORGANIZACIÓN completa.\n"
            "A partir de la NOTA BRUTA transcrita, genera exactamente "
            "cuatro secciones Markdown separadas por el marcador "
            "'###SEPARADOR###' y en este orden:\n"
            "1. RESUMEN: síntesis global de la sesión.\n"
            "2. DATOS_IMPORTANTES: fechas, tareas, avisos, cifras clave.\n"
            "3. GLOSARIO: términos y conceptos abordados con su definición corta.\n"
            "4. CUERPO: todo lo mencionado, organizado en orden de mención.\n"
            "Usa encabezados y listas Markdown. No añadas texto fuera de "
            "las cuatro secciones."
        )
        user = f"NOTA BRUTA:\n```\n{chapter.raw_text}\n```"
        resultado = self._chat(system, user)

        resumen, datos, glosario, cuerpo = self._split_sections(resultado)

        chapter.sectors["resumen"] = resumen
        chapter.sectors["datos_importantes"] = datos
        chapter.sectors["glosario"] = glosario
        chapter.sectors["cuerpo"] = cuerpo if cuerpo else chapter.raw_text
        chapter.transcribed_text = self._render_body(chapter)
        return chapter.sectors

    def _split_sections(self, texto: str) -> tuple[str, str, str, str]:
        """Divide la respuesta del modelo en los 4 sectores."""
        partes = [
            p.strip()
            for p in texto.split("###SEPARADOR###")
            if p.strip() or p
        ] + [""] * 4  # relleno para evitar IndexError

        # Quita encabezados tipo "## Resumen" que el modelo pudiera dejar
        def limpiar(s: str, nombre: str) -> str:
            # {{1,6}} en el f-string produce el cuantificador literal {1,6}
            patron = rf"#{{1,6}}\s*{nombre}\s*"
            sin_titulo = re.sub(patron, "", s, flags=re.I).strip()
            return sin_titulo or ""

        return (
            limpiar(partes[0], "resumen") if partes[0] else "",
            limpiar(partes[1], "datos importantes") if partes[1] else "",
            limpiar(partes[2], "glosario") if partes[2] else "",
            limpiar(partes[3], "cuerpo") if partes[3] else "",
        )

    def build_full_text(self, chapter: Chapter) -> str:
        """Devuelve el texto unificado con todos los sectores."""
        return self._render_body(chapter)


DEFAULT_SYSTEM_PROMPT = (
    "Eres un asistente académico experto. Transcribe y organiza apuntes "
    "de clases de forma clara en Markdown."
)
