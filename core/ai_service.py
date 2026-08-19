"""Servicio de IA (LLM) para Dictonoto.

Conecta con cualquier API compatible con OpenAI (configurable mediante
enlace, modelo, api-key y temperatura). Ofrece una única orquestación de
transcripción:

- ``full_transcription``: toma el texto bruto completo y lo reorganiza en
  los sectores (resumen, datos importantes y glosario), escribiendo el
  resultado final en el ``transcribed_text`` del capítulo.

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
            extra_body={"thinking": {"type": "enabled"}},
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
    # Transcripción completa (reorganiza toda la nota original)
    # ------------------------------------------------------------------
    def full_transcription(self, chapter: Chapter) -> dict:
        """Reorganiza el texto bruto completo en el cuerpo y sus sectores.

        El modelo genera un ÚNICO documento Markdown con los encabezados
        ``## Resumen``, ``## Datos importantes``, ``## Glosario`` y
        ``## Cuerpo``. Ese documento pasa a ser el ``transcribed_text``
        completo (la fuente editable), y los tres primeros encabezados se
        derivan localmente hacia ``chapter.sectors`` reparceando el texto,
        sin que el modelo duplique contenido ni se hagan llamadas extra.

        Devuelve el diccionario de sectores actualizado.
        """
        system = (
            f"{self._system_prompt()}\n\n"
            "Tarea de ORGANIZACIÓN completa.\n"
            "A partir de la NOTA BRUTA transcrita, genera un ÚNICO documento "
            "Markdown que contenga exactamente estos encabezados, en este "
            "orden estricto:\n"
            "## Resumen\n"
            "## Datos importantes\n"
            "## Glosario\n"
            "## Cuerpo\n"
            "Bajo Resumen, una síntesis global de la sesión (puedes usar "
            "párrafos o listas según convenga). Bajo Datos importantes, "
            "fechas, tareas, avisos y cifras clave en formato de lista para "
            "fácil lectura. Bajo Glosario, cada término con su definición "
            "corta, preferiblemente en formato de lista o listas con viñetas. "
            "Bajo Cuerpo, todo lo mencionado en la nota redactado en párrafos "
            "amplios y continuos, fiel al material de origen y en orden de "
            "mención. Usa subtítulos de tercer nivel (###) para separar temas "
            "dentro del cuerpo cuando cambie de asunto, pero bajo cada subtítulo "
            "desarrolla la información en uno o dos párrafos extensos que fluyan "
            "de forma narrativa. NO uses listas de viñetas ni fragmentos pequeños. "
            "Puedes usar negritas ocasionales para resaltar conceptos clave dentro "
            "del texto.\n"
            "No añadas texto fuera de estas cuatro secciones."
        )
        user = f"NOTA BRUTA:\n```\n{chapter.raw_text}\n```"
        resultado = self._chat(system, user)

        chapter.transcribed_text = resultado

        # Derivar los sectores estructurados por parseo local (sin IA extra)
        resumen, datos, glosario, cuerpo = self._split_sections(resultado)
        chapter.sectors["resumen"] = resumen
        chapter.sectors["datos_importantes"] = datos
        chapter.sectors["glosario"] = glosario
        chapter.transcribed_text = cuerpo or chapter.transcribed_text
        return chapter.sectors

    def _split_sections(self, texto: str) -> tuple[str, str, str, str]:
        """Extrae los 4 sectores reparceando los encabezados ``## ...``.

        El cuerpo (lo que cae bajo ``## Cuerpo``) se devuelve como cuarto
        elemento y es el que se usará como ``transcribed_text`` editable.
        """
        orden = {
            "resumen": 0,
            "datos importantes": 1,
            "glosario": 2,
            "cuerpo": 3,
        }
        salida: list[str] = ["", "", "", ""]

        # Localiza los encabezados reconocidos con su rango de contenido
        coincidencias = [
            m for m in re.finditer(
                r"^(#{1,6})\s*(.+?)\s*$", texto, flags=re.M | re.I
            )
            if m.group(2).strip().lower() in orden
        ]

        for i, m in enumerate(coincidencias):
            idx = orden[m.group(2).strip().lower()]
            fin = coincidencias[i + 1].start() if i + 1 < len(coincidencias) else len(texto)
            salida[idx] = texto[m.end():fin].strip()

        # Cuerpo vacío → respaldo con el resto de sectores
        if not salida[3] and any(salida[:3]):
            salida[3] = "\n\n".join(s for s in salida[:3] if s)
        elif not any(salida):
            salida[3] = texto.strip()

        return tuple(salida)  # type: ignore[return-value]


DEFAULT_SYSTEM_PROMPT = (
    "Eres un asistente académico experto. Transcribe y organiza apuntes "
    "de clases de forma clara en Markdown."
)
