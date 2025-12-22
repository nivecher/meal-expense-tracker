# Type stubs for pytesseract
# Generated based on usage in meal expense tracker OCR service

from typing import overload

from PIL import Image

class TesseractNotFoundError(Exception):
    """Exception raised when Tesseract is not found."""

    pass

class pytesseract:
    """Tesseract OCR configuration class."""

    tesseract_cmd: str

def get_tesseract_version() -> str: ...
@overload
def image_to_string(image: Image.Image, config: str = ...) -> str: ...
@overload
def image_to_string(image: str, config: str = ...) -> str: ...
@overload
def image_to_string(image: Image.Image | str, config: str = ...) -> str: ...
