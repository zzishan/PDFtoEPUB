"""
PDFtoEPUB - Convert PDF to fixed-layout EPUB with 100% format preservation
"""

from .converter import PDFtoEPUBConverter, convert_pdf_to_epub
from .pdf_extractor import PDFExtractor
from .epub_generator_v2 import EPUBGeneratorV2
from .validator import ContentValidator

__version__ = "2.0.0"
__author__ = "PDFtoEPUB Team"

__all__ = [
    'PDFtoEPUBConverter',
    'convert_pdf_to_epub',
    'PDFExtractor',
    'EPUBGeneratorV2',
    'ContentValidator'
]
