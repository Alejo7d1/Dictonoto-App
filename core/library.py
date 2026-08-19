"""Gestor de biblioteca: persistencia de Libros y Capítulos en JSON.

Cada libro se guarda como un archivo JSON dentro de ``data/books/``.
"""
import json
import os

from models.book import Book
from models.chapter import Chapter

BOOKS_DIR = "data/books"


class LibraryManager:
    """Carga, guarda y lista los libros de la biblioteca."""

    def __init__(self, books_dir=BOOKS_DIR):
        self.books_dir = books_dir
        os.makedirs(books_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Rutas
    # ------------------------------------------------------------------
    def _file_path(self, name: str) -> str:
        safe = "".join(c for c in name if c not in '\\/:*?"<>|')
        safe = safe.strip().replace(" ", "_") or "libro"
        return os.path.join(self.books_dir, f"{safe}.json")

    # ------------------------------------------------------------------
    # Libros
    # ------------------------------------------------------------------
    def list_books(self) -> list[Book]:
        libros = []
        for fname in os.listdir(self.books_dir):
            if fname.endswith(".json"):
                libro = self._load_file(os.path.join(self.books_dir, fname))
                if libro:
                    libros.append(libro)
        return libros

    def save_book(self, book: Book):
        """Guarda (o crea) el libro en disco."""
        with open(self._file_path(book.name), "w", encoding="utf-8") as f:
            json.dump(book.to_dict(), f, indent=4, ensure_ascii=False)

    def _load_file(self, path: str) -> Book | None:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return Book.from_dict(data)
        except Exception as e:
            print(f"Error al cargar libro {path}: {e}")
            return None
