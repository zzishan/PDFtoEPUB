"""
Fixed-Layout EPUB Generator - Creates EPUB with exact positioning preserved
Uses CSS absolute positioning to maintain PDF layout
"""

import os
import shutil
from pathlib import Path
from typing import List, Dict
from lxml import etree
from zipfile import ZipFile, ZIP_DEFLATED
import mimetypes
from datetime import datetime
import uuid
from .pdf_extractor import PageContent, TextElement, ImageElement


class EPUBGenerator:
    """Generates fixed-layout EPUB files from extracted PDF content"""

    def __init__(self, output_path: str = "output.epub"):
        self.output_path = Path(output_path)
        self.epub_root = Path("/tmp/epub_temp")
        self.meta_inf_dir = self.epub_root / "META-INF"
        self.oebps_dir = self.epub_root / "OEBPS"
        self.images_dir = self.oebps_dir / "images"

        self._setup_structure()

    def _setup_structure(self):
        """Create EPUB directory structure"""
        # Clean and create directories
        if self.epub_root.exists():
            shutil.rmtree(self.epub_root)

        self.meta_inf_dir.mkdir(parents=True, exist_ok=True)
        self.oebps_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)

        # Create mimetype file (must be first, uncompressed)
        mimetype_file = self.epub_root / "mimetype"
        with open(mimetype_file, 'w') as f:
            f.write("application/epub+zip")

    def generate(self, pages_content: List[PageContent], metadata: Dict, images_source_dir: Path) -> str:
        """Generate complete EPUB file"""
        print("Generating EPUB structure...")

        # Copy images to EPUB
        self._copy_images(images_source_dir)

        # Create container.xml
        self._create_container_xml()

        # Create content.opf (package file)
        self._create_package_opf(pages_content, metadata)

        # Create toc.ncx (table of contents)
        self._create_toc_ncx(pages_content)

        # Create individual page XHTML files
        self._create_page_xhtml_files(pages_content)

        # Create CSS stylesheet
        self._create_stylesheet()

        # Package into EPUB
        self._package_epub()

        print(f"EPUB generated: {self.output_path}")
        return str(self.output_path)

    def _copy_images(self, source_dir: Path):
        """Copy extracted images to EPUB images directory"""
        if not source_dir.exists():
            return

        for img_file in source_dir.glob("*.png"):
            if "reference" not in img_file.name:  # Don't include reference images
                shutil.copy(img_file, self.images_dir / img_file.name)

    def _create_container_xml(self):
        """Create META-INF/container.xml"""
        container = etree.Element(
            'container',
            nsmap={
                None: 'urn:oasis:names:tc:opendocument:xmlns:container'
            },
            version='1.0'
        )

        rootfiles = etree.SubElement(container, 'rootfiles')
        etree.SubElement(
            rootfiles,
            'rootfile',
            {
                'full-path': 'OEBPS/content.opf',
                'media-type': 'application/oebps-package+xml'
            }
        )

        container_file = self.meta_inf_dir / "container.xml"
        with open(container_file, 'wb') as f:
            f.write(etree.tostring(container, xml_declaration=True, encoding='UTF-8', pretty_print=True))

    def _create_package_opf(self, pages_content: List[PageContent], metadata: Dict):
        """Create OEBPS/content.opf (package file)"""
        package = etree.Element(
            'package',
            nsmap={
                None: 'http://www.idpf.org/2007/opf',
                'opf': 'http://www.idpf.org/2007/opf',
                'dc': 'http://purl.org/dc/elements/1.1/'
            },
            version='3.0',
            attrib={
                'unique-identifier': 'uuid',
                'prefix': 'rendition: http://www.idpf.org/vocab/rendition/#'
            }
        )

        # Metadata
        metadata_elem = etree.SubElement(package, 'metadata')

        # Unique identifier
        identifier = etree.SubElement(
            metadata_elem,
            '{http://purl.org/dc/elements/1.1/}identifier',
            id='uuid'
        )
        identifier.text = str(uuid.uuid4())

        # Title
        title = etree.SubElement(metadata_elem, '{http://purl.org/dc/elements/1.1/}title')
        title.text = metadata.get('title', 'PDF Conversion')

        # Author
        creator = etree.SubElement(metadata_elem, '{http://purl.org/dc/elements/1.1/}creator')
        creator.text = metadata.get('author', 'Unknown')

        # Modified date
        modified = etree.SubElement(metadata_elem, 'meta', property='dcterms:modified')
        modified.text = datetime.now().isoformat()

        # Fixed-layout rendering
        etree.SubElement(metadata_elem, 'meta', property='rendition:layout').text = 'pre-paginated'
        etree.SubElement(metadata_elem, 'meta', property='rendition:orientation').text = 'portrait'
        etree.SubElement(metadata_elem, 'meta', property='rendition:spread').text = 'none'

        # Manifest
        manifest = etree.SubElement(package, 'manifest')

        # Add CSS
        etree.SubElement(
            manifest,
            'item',
            {
                'id': 'stylesheet',
                'href': 'styles.css',
                'media-type': 'text/css'
            }
        )

        # Add page documents
        for page in pages_content:
            attrs = {
                'id': f'page{page.page_num}',
                'href': f'page{page.page_num:03d}.xhtml',
                'media-type': 'application/xhtml+xml'
            }
            if page.image_elements:
                attrs['properties'] = 'svg'

            etree.SubElement(manifest, 'item', attrs)

        # Add images to manifest
        image_files = set()
        for page in pages_content:
            for img in page.image_elements:
                image_files.add(img.image_path)

        for img_file in image_files:
            mime_type, _ = mimetypes.guess_type(img_file)
            etree.SubElement(
                manifest,
                'item',
                {
                    'id': f'image_{img_file.replace("/", "_").replace(".", "_")}',
                    'href': f'images/{img_file}',
                    'media-type': mime_type or 'image/png'
                }
            )

        # Spine
        spine = etree.SubElement(package, 'spine')
        for page in pages_content:
            etree.SubElement(
                spine,
                'itemref',
                {
                    'idref': f'page{page.page_num}',
                    'properties': 'page-spread-right' if page.page_num % 2 == 1 else 'page-spread-left'
                }
            )

        # Write to file
        opf_file = self.oebps_dir / "content.opf"
        with open(opf_file, 'wb') as f:
            f.write(etree.tostring(package, xml_declaration=True, encoding='UTF-8', pretty_print=True))

    def _create_toc_ncx(self, pages_content: List[PageContent]):
        """Create OEBPS/toc.ncx (table of contents)"""
        ncx = etree.Element(
            'ncx',
            nsmap={'ncx': 'http://www.daisy.org/z3986/2005/ncx/'},
            version='2005-1'
        )

        # Head
        head = etree.SubElement(ncx, 'head')
        uid = etree.SubElement(head, 'meta', name='dtb:uid', content=str(uuid.uuid4()))
        depth = etree.SubElement(head, 'meta', name='dtb:depth', content='1')
        totalPages = etree.SubElement(head, 'meta', name='dtb:totalPageCount', content=str(len(pages_content)))
        maxPageNumber = etree.SubElement(head, 'meta', name='dtb:maxPageNumber', content=str(len(pages_content)))

        # Title
        docTitle = etree.SubElement(ncx, 'docTitle')
        text = etree.SubElement(docTitle, 'text')
        text.text = 'Table of Contents'

        # Nav map
        navMap = etree.SubElement(ncx, 'navMap')
        for page in pages_content:
            navPoint = etree.SubElement(navMap, 'navPoint', id=f'page{page.page_num}', playOrder=str(page.page_num))
            navLabel = etree.SubElement(navPoint, 'navLabel')
            navLabelText = etree.SubElement(navLabel, 'text')
            navLabelText.text = f'Page {page.page_num}'
            content = etree.SubElement(navPoint, 'content', src=f'page{page.page_num:03d}.xhtml')

        # Write to file
        ncx_file = self.oebps_dir / "toc.ncx"
        with open(ncx_file, 'wb') as f:
            f.write(etree.tostring(ncx, xml_declaration=True, encoding='UTF-8', pretty_print=True))

    def _create_page_xhtml_files(self, pages_content: List[PageContent]):
        """Create individual XHTML files for each page"""
        for page in pages_content:
            xhtml = self._generate_page_xhtml(page)
            xhtml_file = self.oebps_dir / f"page{page.page_num:03d}.xhtml"

            with open(xhtml_file, 'wb') as f:
                f.write(etree.tostring(xhtml, xml_declaration=True, encoding='UTF-8', pretty_print=True))

    def _generate_page_xhtml(self, page: PageContent) -> etree._Element:
        """Generate XHTML for a single page with absolute positioning"""
        html = etree.Element(
            'html',
            nsmap={
                None: 'http://www.w3.org/1999/xhtml',
                'epub': 'http://www.idpf.org/2007/ops'
            }
        )

        # Head
        head = etree.SubElement(html, 'head')
        meta_charset = etree.SubElement(head, 'meta', charset='utf-8')
        meta_viewport = etree.SubElement(head, 'meta', name='viewport', content=f'width={page.page_width}, height={page.page_height}')
        title = etree.SubElement(head, 'title')
        title.text = f'Page {page.page_num}'
        link = etree.SubElement(head, 'link', rel='stylesheet', href='styles.css', type='text/css')

        # Body
        body = etree.SubElement(html, 'body')

        # Page container with absolute dimensions
        page_div = etree.SubElement(
            body,
            'div',
            {
                'class': 'page',
                'id': f'page{page.page_num}',
                'style': f'width: {page.page_width}px; height: {page.page_height}px; position: relative;'
            }
        )

        # Add images first (background layer)
        for img in page.image_elements:
            self._add_image_to_page(page_div, img)

        # Add text elements (foreground layer)
        for text_elem in page.text_elements:
            self._add_text_to_page(page_div, text_elem)

        return html

    def _add_image_to_page(self, parent: etree._Element, img: ImageElement):
        """Add an image with absolute positioning"""
        img_div = etree.SubElement(
            parent,
            'div',
            {
                'class': 'image-element',
                'style': self._get_position_style(img.x0, img.y0, img.width, img.height)
            }
        )

        img_elem = etree.SubElement(
            img_div,
            'img',
            {
                'src': f'images/{img.image_path}',
                'alt': 'Image',
                'style': f'width: {img.width}px; height: {img.height}px; display: block;'
            }
        )

    def _add_text_to_page(self, parent: etree._Element, text: TextElement):
        """Add text element with absolute positioning"""
        width = text.x1 - text.x0
        height = text.y1 - text.y0

        style = self._get_position_style(text.x0, text.y0, width, height)

        # Add font styling
        font_style = f'{style} font-size: {text.font_size}px; line-height: {text.line_height}px;'
        if text.is_bold:
            font_style += ' font-weight: bold;'
        if text.is_italic:
            font_style += ' font-style: italic;'

        text_div = etree.SubElement(
            parent,
            'div',
            {
                'class': 'text-element',
                'style': font_style
            }
        )
        text_div.text = text.text

    def _get_position_style(self, x: float, y: float, width: float, height: float) -> str:
        """Generate CSS positioning style"""
        return f'position: absolute; left: {x}px; top: {y}px; width: {width}px; height: {height}px;'

    def _create_stylesheet(self):
        """Create OEBPS/styles.css"""
        css_content = """/* Fixed-Layout EPUB Stylesheet */

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

html, body {
    width: 100%;
    height: 100%;
    overflow: hidden;
}

body {
    font-family: 'Georgia', serif;
    background-color: #ffffff;
}

.page {
    page-break-after: always;
    page-break-inside: avoid;
    background-color: #ffffff;
}

.text-element {
    overflow: hidden;
    word-wrap: break-word;
    white-space: normal;
    color: #000000;
}

.image-element {
    overflow: hidden;
}

.image-element img {
    object-fit: contain;
}

/* Preserve exact text rendering */
body {
    -webkit-text-size-adjust: 100%;
    -moz-text-size-adjust: 100%;
    text-size-adjust: 100%;
}
"""

        css_file = self.oebps_dir / "styles.css"
        with open(css_file, 'w') as f:
            f.write(css_content)

    def _package_epub(self):
        """Package the EPUB directory into a ZIP file"""
        # Create output directory if needed
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create EPUB ZIP file
        with ZipFile(str(self.output_path), 'w', ZIP_DEFLATED) as epub:
            # Add mimetype first (uncompressed)
            mimetype_file = self.epub_root / "mimetype"
            epub.write(mimetype_file, arcname="mimetype", compress_type=0)

            # Add all other files
            for root, dirs, files in os.walk(str(self.epub_root)):
                for file in files:
                    if file == "mimetype":
                        continue

                    file_path = Path(root) / file
                    arcname = file_path.relative_to(self.epub_root)
                    epub.write(file_path, arcname=arcname)

        # Cleanup temp directory
        shutil.rmtree(self.epub_root)
