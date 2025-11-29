"""
Main PDF to EPUB Converter
Orchestrates the conversion pipeline with validation
"""

import sys
from pathlib import Path
from typing import Tuple
import json
import logging
from .pdf_extractor import PDFExtractor
from .epub_generator_v2 import EPUBGeneratorV2
from .validator import ContentValidator

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PDFtoEPUBConverter:
    """Main converter class"""

    def __init__(self, pdf_path: str, output_epub_path: str = None, working_dir: str = "conversion_work"):
        self.pdf_path = Path(pdf_path)
        self.output_epub_path = Path(output_epub_path) if output_epub_path else self.pdf_path.with_suffix('.epub')
        self.working_dir = Path(working_dir)

        # Validate input
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {self.pdf_path}")

        logger.info(f"Converter initialized for: {self.pdf_path}")

    def convert(self, validate: bool = True) -> str:
        """
        Convert PDF to EPUB with optional validation

        Args:
            validate: Whether to validate output integrity

        Returns:
            Path to generated EPUB file
        """
        try:
            # Step 1: Extract content from PDF
            logger.info("Step 1/4: Extracting PDF content...")
            extractor = PDFExtractor(str(self.pdf_path), output_dir=str(self.working_dir / "extracted"))
            pages_content, metadata = extractor.extract_all()
            logger.info(f"Extracted {len(pages_content)} pages")

            # Step 2: Generate EPUB
            logger.info("Step 2/4: Generating EPUB structure...")
            generator = EPUBGeneratorV2(output_path=str(self.output_epub_path))
            epub_path = generator.generate(
                pages_content,
                metadata,
                self.working_dir / "extracted" / "images"
            )
            logger.info(f"EPUB created: {epub_path}")

            # Step 3: Validate (optional)
            if validate:
                logger.info("Step 3/4: Validating EPUB integrity...")
                validator = ContentValidator(str(self.pdf_path), epub_path)
                report = validator.validate()

                # Save validation report
                report_path = self.working_dir / "validation_report.json"
                report_path.parent.mkdir(parents=True, exist_ok=True)
                with open(report_path, 'w') as f:
                    json.dump(report, f, indent=2)

                logger.info(f"Validation report saved to: {report_path}")

                if not report['overall_status']:
                    logger.warning("Validation found issues. Check report for details.")
            else:
                logger.info("Step 3/4: Skipping validation")

            logger.info(f"Step 4/4: Conversion complete!")
            logger.info(f"Output EPUB: {self.output_epub_path}")

            return str(self.output_epub_path)

        except Exception as e:
            logger.error(f"Conversion failed: {e}", exc_info=True)
            raise

    def get_summary(self) -> dict:
        """Get conversion summary"""
        return {
            'input_pdf': str(self.pdf_path),
            'output_epub': str(self.output_epub_path),
            'working_directory': str(self.working_dir),
            'output_exists': self.output_epub_path.exists(),
            'output_size_mb': self.output_epub_path.stat().st_size / (1024*1024) if self.output_epub_path.exists() else 0
        }


def convert_pdf_to_epub(pdf_path: str, output_epub_path: str = None, validate: bool = True) -> str:
    """
    Convenience function to convert PDF to EPUB

    Args:
        pdf_path: Path to input PDF file
        output_epub_path: Path to output EPUB file (optional)
        validate: Whether to validate output integrity

    Returns:
        Path to generated EPUB file
    """
    converter = PDFtoEPUBConverter(pdf_path, output_epub_path)
    return converter.convert(validate=validate)
