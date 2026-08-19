from models.chapter import Chapter


class Book:
    def __init__(self, name, description="", color_hex="#3B82F6"):
        self.name = name
        self.description = description
        self.color_hex = color_hex
        self.chapters = []  # Lista de objetos Chapter

    def add_chapter(self, chapter):
        self.chapters.append(chapter)

    def to_dict(self):
        """Convierte el libro y sus capítulos en JSON."""
        return {
            "name": self.name,
            "description": self.description,
            "color_hex": self.color_hex,
            "chapters": [ch.to_dict() for ch in self.chapters]
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Book":
        """Reconstruye un libro desde un diccionario (JSON)."""
        book = cls(
            name=data.get("name", "Libro"),
            description=data.get("description", ""),
            color_hex=data.get("color_hex", "#3B82F6"),
        )
        for ch_data in data.get("chapters", []):
            book.add_chapter(Chapter.from_dict(ch_data))
        return book