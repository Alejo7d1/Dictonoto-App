import json
import os

CONFIG_FILE = "config/settings.json"

DEFAULT_CONFIG = {
    "ai": {
        "api_key": "",
        "base_url": "",
        "model": "",
        "temperature": 0.3,
        "system_prompt": "Eres un asistente académico experto. Transcribe y organiza apuntes de clases de forma clara en Markdown."
    },
    "recording": {
        "silence_pause_seconds": 6,
        "max_fragment_seconds": 12,
        "auto_quick_transcription": True,
        "whisper_model": "small",
        "device": "auto",
        "input_device": None
    }
}

class ConfigManager:
    def __init__(self, filepath=CONFIG_FILE):
        self.filepath = filepath
        self.config = self.load_config()

    def load_config(self):
        """Carga el archivo de configuración. Si no existe, crea el predeterminado."""
        if not os.path.exists(self.filepath):
            self.save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG
        
        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error al cargar configuración ({e}), usando valores por defecto.")
            return DEFAULT_CONFIG

    def save_config(self, new_config):
        """Guarda los cambios en el archivo settings.json."""
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(new_config, f, indent=4, ensure_ascii=False)
        self.config = new_config

    def get(self, category, key, default=None):
        """Obtiene un valor específico (ej. config.get('ai', 'api_key'))."""
        return self.config.get(category, {}).get(key, default)
