# Type stubs for PyMuPDF (fitz)
# Generated based on usage in meal expense tracker OCR service

from typing import overload

class Document:
    """PDF document class."""

    def __init__(
        self, filename: str | None = None, stream: bytes | None = None, filetype: str | None = None
    ) -> None: ...
    def __len__(self) -> int: ...
    def __getitem__(self, index: int) -> Page: ...
    def close(self) -> None: ...

class Page:
    """PDF page class."""

    def get_text(self) -> str: ...
    def get_images(self, full: bool = False) -> list: ...
    def get_pixmap(self, matrix: Matrix | None = None, alpha: bool = False, annots: bool = True) -> Pixmap: ...

class Pixmap:
    """Image pixmap class."""

    width: int
    height: int
    samples: bytes

    def tobytes(self, output: str = "png") -> bytes: ...

class Matrix:
    """Transformation matrix class."""

    def __init__(
        self,
        sx: float,
        sy: float,
        rot: float = 0,
        m11: float = 0,
        m12: float = 0,
        m21: float = 0,
        m22: float = 0,
        dx: float = 0,
        dy: float = 0,
    ) -> None: ...

# Module-level functions
@overload
def open(filename: str, filetype: str | None = None) -> Document: ...
@overload
def open(stream: bytes, filetype: str) -> Document: ...
@overload
def open(filename: str | bytes | None = None, stream: bytes | None = None, filetype: str | None = None) -> Document: ...
