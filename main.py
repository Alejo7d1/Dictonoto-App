"""Punto de entrada de Dictonoto.

Lanza la interfaz gráfica. Si se pasa --test, ejecuta una verificación
rápida de la arquitectura (config, modelos) sin abrir la ventana.
"""
import sys


def test_inicial():
    """Prueba rápida de configuración y modelos (sin UI)."""
    from config.config_manager import ConfigManager
    from models.book import Book
    from models.chapter import Chapter

    print("=" * 20)
    print("  INICIANDO ARQUITECTURA DE DICTONOTO  ")
    print("=" * 20)

    config_mgr = ConfigManager()
    api_url = config_mgr.get("ai", "base_url")
    pausa = config_mgr.get("recording", "silence_pause_seconds")

    print(f"\n[Configuración Cargada]")
    print(f" -> URL de IA: {api_url}")
    print(f" -> Tiempo de pausa para transcripción rápida: {pausa}s")

    mi_libro = Book(
        name="Redes de Computadoras",
        description="Clases del ciclo actual",
        color_hex="#FF5733",
    )
    mi_capitulo = Chapter(title="Clase 1: Modelo OSI vs TCP/IP")
    mi_capitulo.raw_text = "hoy vamos a ver el modelo osi que tiene siete capas..."
    mi_capitulo.transcribed_text = "## Modelo OSI\nEl profesor introdujo las 7 capas..."
    mi_libro.add_chapter(mi_capitulo)

    print(f"\n[Estructura Probada]")
    print(f" -> Libro: {mi_libro.name} ({len(mi_libro.chapters)} capítulo/s)")
    print(f" -> Capítulo 1: {mi_libro.chapters[0].title}")
    print("\n✅ ¡Todo cimentado correctamente!")


if __name__ == "__main__":
    if "--test" in sys.argv:
        test_inicial()
    else:
        from app import main
        main()