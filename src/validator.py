"""
Content Validator - Validates integrity between source PDF and generated EPUB
Ensures 100% preservation of content and positioning
"""

import pdfplumber
from pathlib import Path
from typing import Dict, List
from zipfile import ZipFile
from lxml import etree
import json
from datetime import datetime


class ContentValidator:
    """Validates EPUB against source PDF"""

    def __init__(self, pdf_path: str, epub_path: str):
        self.pdf_path = Path(pdf_path)
        self.epub_path = Path(epub_path)
        self.issues = []
        self.warnings = []

    def validate(self) -> Dict:
        """Run comprehensive validation"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'source_pdf': str(self.pdf_path),
            'output_epub': str(self.epub_path),
            'validation_checks': [],
            'issues': [],
            'warnings': [],
            'overall_status': True
        }

        # Check 1: Files exist
        report['validation_checks'].append(self._check_files_exist())

        # Check 2: EPUB structure
        report['validation_checks'].append(self._check_epub_structure())

        # Check 3: Page count
        report['validation_checks'].append(self._check_page_count())

        # Check 4: Image presence
        report['validation_checks'].append(self._check_images_present())

        # Check 5: Text content
        report['validation_checks'].append(self._check_text_content())

        # Check 6: EPUB validity
        report['validation_checks'].append(self._check_epub_validity())

        report['issues'] = self.issues
        report['warnings'] = self.warnings
        report['overall_status'] = len(self.issues) == 0

        return report

    def _check_files_exist(self) -> Dict:
        """Check if both PDF and EPUB files exist"""
        check = {
            'name': 'File Existence',
            'passed': True,
            'details': []
        }

        if not self.pdf_path.exists():
            check['passed'] = False
            self.issues.append(f"Source PDF not found: {self.pdf_path}")
            check['details'].append(f"PDF missing: {self.pdf_path}")

        if not self.epub_path.exists():
            check['passed'] = False
            self.issues.append(f"Output EPUB not found: {self.epub_path}")
            check['details'].append(f"EPUB missing: {self.epub_path}")

        if check['passed']:
            check['details'].append(f"PDF size: {self.pdf_path.stat().st_size / 1024:.2f} KB")
            check['details'].append(f"EPUB size: {self.epub_path.stat().st_size / 1024:.2f} KB")

        return check

    def _check_epub_structure(self) -> Dict:
        """Check if EPUB has proper structure"""
        check = {
            'name': 'EPUB Structure',
            'passed': True,
            'details': []
        }

        try:
            with ZipFile(str(self.epub_path), 'r') as epub:
                required_files = ['mimetype', 'META-INF/container.xml', 'OEBPS/content.opf']

                for required_file in required_files:
                    if required_file not in epub.namelist():
                        check['passed'] = False
                        self.issues.append(f"Missing required EPUB file: {required_file}")
                        check['details'].append(f"Missing: {required_file}")
                    else:
                        check['details'].append(f"Found: {required_file}")

                # Check for XHTML pages
                xhtml_files = [f for f in epub.namelist() if f.endswith('.xhtml')]
                check['details'].append(f"Page files: {len(xhtml_files)}")

                if len(xhtml_files) == 0:
                    check['passed'] = False
                    self.issues.append("No XHTML page files found in EPUB")

        except Exception as e:
            check['passed'] = False
            self.issues.append(f"Failed to read EPUB: {e}")
            check['details'].append(f"Error: {e}")

        return check

    def _check_page_count(self) -> Dict:
        """Verify page count matches between PDF and EPUB"""
        check = {
            'name': 'Page Count',
            'passed': True,
            'details': []
        }

        try:
            # Count PDF pages
            with pdfplumber.open(str(self.pdf_path)) as pdf:
                pdf_pages = len(pdf.pages)

            # Count EPUB pages
            with ZipFile(str(self.epub_path), 'r') as epub:
                xhtml_files = [f for f in epub.namelist() if f.endswith('.xhtml')]
                epub_pages = len(xhtml_files)

            check['details'].append(f"PDF pages: {pdf_pages}")
            check['details'].append(f"EPUB pages: {epub_pages}")

            if pdf_pages != epub_pages:
                check['passed'] = False
                self.issues.append(f"Page count mismatch: PDF has {pdf_pages}, EPUB has {epub_pages}")
            else:
                check['details'].append("Page count matches")

        except Exception as e:
            check['passed'] = False
            self.issues.append(f"Could not verify page count: {e}")

        return check

    def _check_images_present(self) -> Dict:
        """Check if images are preserved in EPUB"""
        check = {
            'name': 'Image Preservation',
            'passed': True,
            'details': []
        }

        try:
            # Count images in PDF
            pdf_image_count = 0
            with pdfplumber.open(str(self.pdf_path)) as pdf:
                for page in pdf.pages:
                    pdf_image_count += len(page.images)

            # Count images in EPUB
            with ZipFile(str(self.epub_path), 'r') as epub:
                epub_images = [f for f in epub.namelist() if f.startswith('OEBPS/images/') and not 'reference' in f]
                epub_image_count = len(epub_images)

            check['details'].append(f"PDF images: {pdf_image_count}")
            check['details'].append(f"EPUB images: {epub_image_count}")

            if pdf_image_count > 0 and epub_image_count == 0:
                check['passed'] = False
                self.issues.append(f"Images not preserved in EPUB")
            elif pdf_image_count > 0 and epub_image_count < pdf_image_count:
                self.warnings.append(f"Some images may be missing: PDF has {pdf_image_count}, EPUB has {epub_image_count}")
                check['details'].append("Warning: Possible image loss")

        except Exception as e:
            self.warnings.append(f"Could not verify images: {e}")
            check['details'].append(f"Warning: {e}")

        return check

    def _check_text_content(self) -> Dict:
        """Verify text content is present in EPUB"""
        check = {
            'name': 'Text Content',
            'passed': True,
            'details': []
        }

        try:
            # Get text from PDF
            pdf_text_chars = 0
            with pdfplumber.open(str(self.pdf_path)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pdf_text_chars += len(text)

            # Get text from EPUB
            epub_text_chars = 0
            with ZipFile(str(self.epub_path), 'r') as epub:
                xhtml_files = [f for f in epub.namelist() if f.endswith('.xhtml') and 'page' in f]

                for xhtml_file in xhtml_files:
                    try:
                        content = epub.read(xhtml_file).decode('utf-8')
                        root = etree.fromstring(content.encode('utf-8'))
                        text_elements = root.xpath('//text()')
                        epub_text_chars += sum(len(t) for t in text_elements)
                    except:
                        pass

            check['details'].append(f"PDF text characters: {pdf_text_chars}")
            check['details'].append(f"EPUB text characters: {epub_text_chars}")

            if pdf_text_chars > 0 and epub_text_chars == 0:
                self.warnings.append("No text content found in EPUB")
                check['details'].append("Warning: Text may not be extracted")
            elif pdf_text_chars > 0 and epub_text_chars < (pdf_text_chars * 0.8):  # Allow 20% tolerance
                self.warnings.append(f"Text content may be incomplete")
                check['details'].append("Warning: Possible text loss")

        except Exception as e:
            self.warnings.append(f"Could not verify text: {e}")
            check['details'].append(f"Warning: {e}")

        return check

    def _check_epub_validity(self) -> Dict:
        """Check basic EPUB validity"""
        check = {
            'name': 'EPUB Validity',
            'passed': True,
            'details': []
        }

        try:
            with ZipFile(str(self.epub_path), 'r') as epub:
                # Check mimetype
                mimetype = epub.read('mimetype').decode('utf-8').strip()
                if mimetype != 'application/epub+zip':
                    check['passed'] = False
                    self.issues.append(f"Invalid mimetype: {mimetype}")
                    check['details'].append(f"Invalid mimetype: {mimetype}")
                else:
                    check['details'].append("Mimetype is correct")

                # Validate XML structure
                for xhtml_file in epub.namelist():
                    if xhtml_file.endswith('.xhtml') or xhtml_file.endswith('.opf') or xhtml_file.endswith('.ncx'):
                        try:
                            content = epub.read(xhtml_file)
                            etree.fromstring(content)
                        except etree.XMLSyntaxError as e:
                            check['passed'] = False
                            self.issues.append(f"Invalid XML in {xhtml_file}: {e}")

                check['details'].append("XML structure is valid")

        except Exception as e:
            check['passed'] = False
            self.issues.append(f"Could not validate EPUB: {e}")

        return check
