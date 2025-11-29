"""
InDesign EPUB Fixer - Fixes positioning and fonts while keeping fixed-layout structure
"""

import zipfile
import os
import shutil
from pathlib import Path
from lxml import etree
import re
from typing import Dict, List

class InDesignEPUBFixer:
    """Fixes InDesign-exported EPUBs by correcting positioning and fonts"""

    def __init__(self, input_epub: str, output_epub: str = None):
        self.input_epub = input_epub
        self.output_epub = output_epub or input_epub.replace('.epub', '_fixed.epub')
        self.work_dir = Path('/tmp/indesign_epub_work')
        self.ns = {
            'xhtml': 'http://www.w3.org/1999/xhtml',
            'epub': 'http://www.idpf.org/2007/ops',
            'opf': 'http://www.idpf.org/2007/opf',
            'dc': 'http://purl.org/dc/elements/1.1/',
            'container': 'urn:oasis:names:tc:opendocument:xmlns:container'
        }

    def fix(self):
        """Main entry point for fixing the EPUB"""
        print(f"Fixing InDesign EPUB: {self.input_epub}")

        # Extract EPUB
        self._extract_epub()

        # Fix XHTML files
        self._fix_xhtml_files()

        # Fix CSS
        self._fix_css()

        # Replace custom fonts with system fonts
        self._fix_fonts()

        # Repackage EPUB
        self._repackage_epub()

        print(f"✓ Fixed EPUB saved to: {self.output_epub}")

    def _extract_epub(self):
        """Extract EPUB to temporary directory"""
        if self.work_dir.exists():
            shutil.rmtree(self.work_dir)
        self.work_dir.mkdir(parents=True)

        with zipfile.ZipFile(self.input_epub, 'r') as zip_ref:
            zip_ref.extractall(self.work_dir)

    def _fix_xhtml_files(self):
        """Fix positioning in XHTML files"""
        oebps_dir = self.work_dir / 'OEBPS'
        xhtml_files = list(oebps_dir.glob('*.xhtml'))

        print(f"  Processing {len(xhtml_files)} XHTML files...")

        for xhtml_file in xhtml_files:
            if 'toc' in xhtml_file.name:
                continue
            self._fix_xhtml_file(xhtml_file)

    def _fix_xhtml_file(self, xhtml_path: Path):
        """Fix positioning and fonts in a single XHTML file"""
        try:
            parser = etree.XMLParser(remove_blank_text=False)
            tree = etree.parse(str(xhtml_path), parser)
            root = tree.getroot()

            # Process all divs with transform styles
            for div in root.iter():
                if div.tag.endswith('}div') or div.tag == 'div':
                    style = div.get('style', '')
                    if style:
                        # Fix the transforms: change scale(0.05) to scale(1) to make text readable
                        # But keep the positioning
                        style = self._fix_transform_style(style)
                        div.set('style', style)

                # Replace custom font families
                if 'class' in div.attrib:
                    div.attrib['class'] = self._fix_font_classes(div.attrib['class'])

            # Fix spans with font-family
            for span in root.iter():
                if span.tag.endswith('}span') or span.tag == 'span':
                    style = span.get('style', '')
                    if 'font-family' in style:
                        style = self._replace_fonts(style)
                        span.set('style', style)

            # Write back
            with open(xhtml_path, 'wb') as f:
                tree.write(f, encoding='UTF-8', xml_declaration=True, standalone=True)

        except Exception as e:
            print(f"    Warning: Could not fix {xhtml_path.name}: {e}")

    def _fix_transform_style(self, style: str) -> str:
        """Fix CSS transforms to make content readable while preserving layout structure"""
        # Remove the scale(0.05) that makes everything tiny
        # but keep positioning information

        # Extract the translate values
        translate_match = re.search(r'translate\(([^)]+)\)', style)
        translate_vals = translate_match.group(1) if translate_match else "0,0"

        # Remove all transform-related properties
        style = re.sub(r'-webkit-transform\s*:[^;]*;?', '', style)
        style = re.sub(r'transform\s*:[^;]*;?', '', style)
        style = re.sub(r'-webkit-transform-origin\s*:[^;]*;?', '', style)
        style = re.sub(r'transform-origin\s*:[^;]*;?', '', style)

        # Clean up whitespace
        style = re.sub(r';\s*;', ';', style).strip().rstrip(';')

        return style

    def _fix_font_classes(self, class_str: str) -> str:
        """Fix font-related class names"""
        return class_str

    def _replace_fonts(self, style: str) -> str:
        """Replace custom font families with standard ones"""
        style = re.sub(r'font-family\s*:\s*["\']?AauxNext[^"\']*["\']?',
                      "font-family: 'Georgia', 'Times New Roman', serif", style)
        style = re.sub(r'font-family\s*:\s*["\']?Alga[^"\']*["\']?',
                      "font-family: -apple-system, 'Segoe UI', Arial, sans-serif", style)
        return style

    def _fix_css(self):
        """Fix CSS file"""
        css_path = self.work_dir / 'OEBPS' / 'css' / 'idGeneratedStyles.css'

        if not css_path.exists():
            return

        print("  Fixing CSS...")

        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()

        # Replace font-family declarations
        css_content = re.sub(
            r'font-family\s*:\s*["\']?AauxNext[^;]*;',
            "font-family: 'Georgia', 'Times New Roman', serif;",
            css_content
        )
        css_content = re.sub(
            r'font-family\s*:\s*["\']?Alga[^;]*;',
            "font-family: -apple-system, 'Segoe UI', Arial, sans-serif;",
            css_content
        )

        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(css_content)

    def _fix_fonts(self):
        """Remove custom font files from EPUB"""
        print("  Removing custom fonts...")

        # Remove font directory
        font_dir = self.work_dir / 'OEBPS' / 'font'
        if font_dir.exists():
            shutil.rmtree(font_dir)

        # Update content.opf to remove font references
        opf_path = self.work_dir / 'OEBPS' / 'content.opf'
        if opf_path.exists():
            try:
                parser = etree.XMLParser(remove_blank_text=False)
                tree = etree.parse(str(opf_path), parser)
                root = tree.getroot()

                # Remove font items from manifest
                manifest = root.find('.//opf:manifest', self.ns)
                if manifest is not None:
                    items_to_remove = []
                    for item in manifest.findall('opf:item', self.ns):
                        href = item.get('href', '')
                        if '.otf' in href or '.ttf' in href:
                            items_to_remove.append(item)

                    for item in items_to_remove:
                        manifest.remove(item)

                with open(opf_path, 'wb') as f:
                    tree.write(f, encoding='UTF-8', xml_declaration=True, standalone=True)
            except Exception as e:
                print(f"    Warning: Could not update OPF: {e}")

    def _repackage_epub(self):
        """Repackage the fixed EPUB"""
        print("  Repackaging EPUB...")

        if Path(self.output_epub).exists():
            os.remove(self.output_epub)

        with zipfile.ZipFile(self.output_epub, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add mimetype first (stored, not compressed)
            mimetype_path = self.work_dir / 'mimetype'
            if mimetype_path.exists():
                zipf.write(mimetype_path, 'mimetype', compress_type=zipfile.ZIP_STORED)

            # Add all other files
            for root_dir, dirs, files in os.walk(self.work_dir):
                for file in files:
                    file_path = os.path.join(root_dir, file)
                    arcname = os.path.relpath(file_path, self.work_dir)

                    if arcname != 'mimetype':
                        zipf.write(file_path, arcname, compress_type=zipfile.ZIP_DEFLATED)


def fix_indesign_epub(input_epub: str, output_epub: str = None):
    """Convenience function to fix an InDesign EPUB"""
    fixer = InDesignEPUBFixer(input_epub, output_epub)
    fixer.fix()
    return fixer.output_epub
