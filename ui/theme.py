"""Tema centralizado para la aplicación."""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class Colors:
    # Fondo
    bg_primary: str = "#121212"
    bg_panel: str = "#1e1e1e"
    bg_panel_light: str = "#2a2a2a"
    bg_panel_dark: str = "#161616"
    bg_card: str = "#262626"
    
    # Texto
    text_primary: str = "#f0f0f0"
    text_secondary: str = "#b0b0b0"
    text_muted: str = "#7a7a7a"
    text_inverse: str = "#ffffff"
    
    # Acento
    accent: str = "#191951"
    accent_hover: str = "#270dea"
    accent_light: str = "#8b7cf7"
    
    # Estados
    success: str = "#2ecc71"
    success_dark: str = "#27ae60"
    warning: str = "#f39c12"
    danger: str = "#e74c3c"
    danger_dark: str = "#c0392b"
    
    # Bordes
    border: str = "#333333"
    border_light: str = "#444444"
    
    # Sombra
    shadow: str = "rgba(0,0,0,0.3)"


@dataclass(frozen=True)
class Spacing:
    xs: int = 4
    sm: int = 8
    md: int = 14
    lg: int = 20
    xl: int = 28


@dataclass(frozen=True)
class BorderRadius:
    none: int = 0
    sm: int = 4
    md: int = 8
    lg: int = 12
    xl: int = 16


@dataclass(frozen=True)
class Sizes:
    button_small: int = 80
    button_medium: int = 110
    button_large: int = 160
    
    raw_panel_width_ratio: float = 0.33
    body_panel_width_ratio: float = 0.67


# Clase para fuentes - se instancia cuando se necesita
class Fonts:
    """Fuentes de la aplicación - se instancian bajo demanda."""
    _instance: Optional["Fonts"] = None
    _fonts: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __getattr__(self, name: str):
        """Devuelve una fuente CTkFont, creándola si no existe."""
        from customtkinter import CTkFont
        
        if name in self._fonts:
            return self._fonts[name]
        
        # Configuración de fuentes
        font_config = {
            "heading_large": {"size": 20, "weight": "bold"},
            "heading_medium": {"size": 18, "weight": "bold"},
            "heading_small": {"size": 14, "weight": "bold"},
            "body_large": {"size": 14},
            "body": {"size": 13},
            "body_small": {"size": 12},
            "caption": {"size": 11},
            "mono": {"size": 13, "family": "Consolas"},
        }
        
        if name not in font_config:
            raise AttributeError(f"Font '{name}' not defined")
        
        font = CTkFont(**font_config[name])
        self._fonts[name] = font
        return font
    
# Función helper para obtener fuentes
def get_font(style: str) -> "CTkFont":
    """Obtiene una fuente del tema. Debe llamarse después de inicializar Tk."""
    from customtkinter import CTkFont
    
    font_config = {
        "heading_large": {"size": 20, "weight": "bold"},
        "heading_medium": {"size": 18, "weight": "bold"},
        "heading_small": {"size": 14, "weight": "bold"},
        "body_large": {"size": 14},
        "body": {"size": 13},
        "body_small": {"size": 12},
        "caption": {"size": 11},
        "mono": {"size": 13, "family": "Consolas"},
    }
    
    if style not in font_config:
        return CTkFont(size=13)
    
    return CTkFont(**font_config[style])


# Instancias globales
colors = Colors()
spacing = Spacing()
radius = BorderRadius()
sizes = Sizes()
fonts = Fonts()  # Singleton que crea fuentes bajo demanda
# Alias para compatibilidad: los módulos importan `typography.body`,
# `typography.heading_medium`, etc., resueltos por Fonts.__getattr__
typography = fonts