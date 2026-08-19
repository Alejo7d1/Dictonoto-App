import time

class Chapter:
    def __init__(self, title="Capítulo Sin Título"):
        self.title = title
        self.timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Las 2 hojas principales
        self.raw_text = ""         # Hoja 1: Texto bruto (sin limpiar)
        self.transcribed_text = "" # Hoja 2: Texto limpio / formateado
        
        # Los 4 sectores informativos
        self.sectors = {
            "cuerpo": "",            # Todo organizado en orden cronológico
            "datos_importantes": "",  # Fechas, tareas, avisos
            "glosario": "",          # Términos y conceptos clave
            "resumen": ""            # Síntesis global (se llena en transcripción completa)
        }

    def to_dict(self):
        """Convierte el capítulo en diccionario para guardarlo en JSON."""
        return {
            "title": self.title,
            "timestamp": self.timestamp,
            "raw_text": self.raw_text,
            "transcribed_text": self.transcribed_text,
            "sectors": self.sectors
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Chapter":
        """Reconstruye un capítulo desde un diccionario (JSON)."""
        ch = cls(title=data.get("title", "Capítulo Sin Título"))
        ch.timestamp = data.get("timestamp", ch.timestamp)
        ch.raw_text = data.get("raw_text", "")
        ch.transcribed_text = data.get("transcribed_text", "")
        ch.sectors = data.get("sectors", ch.sectors)
        return ch