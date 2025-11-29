"""
Fixed-Layout EPUB Generator V2 - Apple Books Compatible
Creates EPUB with exact positioning preserved and proper EPUB 3.0 compliance
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


class EPUBGeneratorV2:
    """Generates fixed-layout EPUB files with Apple Books compatibility"""

    def __init__(self, output_path: str = "output.epub"):
        self.output_path = Path(output_path)
        self.epub_root = Path("/tmp/epub_temp_v2")
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

        # Create mimetype file (must be first, uncompressed, EXACTLY this text)
        mimetype_file = self.epub_root / "mimetype"
        with open(mimetype_file, 'wb') as f:
            # Write as binary to ensure no extra bytes
            f.write(b"application/epub+zip")

    def generate(self, pages_content: List[PageContent], metadata: Dict, images_source_dir: Path) -> str:
        """Generate complete EPUB file"""
        print("Generating Apple Books compatible EPUB...")

        # Copy images to EPUB
        self._copy_images(images_source_dir)

        # Create container.xml
        self._create_container_xml()

        # Create content.opf (package file)
        self._create_package_opf(pages_content, metadata)

        # Create toc.ncx (table of contents - for backward compatibility)
        self._create_toc_ncx(pages_content)

        # Create nav.xhtml (EPUB 3.0 required)
        self._create_nav_xhtml(pages_content)

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

        # Copy PNG images (no compression in extraction)
        for img_file in source_dir.glob("*.png"):
            if "reference" not in img_file.name:
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
        """Create OEBPS/content.opf (package file) - EPUB 3.0 compliant"""
        package = etree.Element(
            'package',
            nsmap={
                None: 'http://www.idpf.org/2007/opf',
                'opf': 'http://www.idpf.org/2007/opf',
                'dc': 'http://purl.org/dc/elements/1.1/'
            },
            version='3.0'
        )

        package.set('unique-identifier', 'uuid')
        package.set('prefix', 'rendition: http://www.idpf.org/vocab/rendition/#')

        # Metadata
        metadata_elem = etree.SubElement(package, 'metadata')

        # Required: Unique identifier
        identifier = etree.SubElement(
            metadata_elem,
            '{http://purl.org/dc/elements/1.1/}identifier',
            id='uuid'
        )
        identifier.text = str(uuid.uuid4())

        # Title
        title = etree.SubElement(metadata_elem, '{http://purl.org/dc/elements/1.1/}title')
        title.text = metadata.get('title', 'PDF Document')

        # Author/Creator
        if metadata.get('author') and metadata.get('author') != 'Unknown':
            creator = etree.SubElement(metadata_elem, '{http://purl.org/dc/elements/1.1/}creator')
            creator.text = metadata.get('author')

        # Language
        language = etree.SubElement(metadata_elem, '{http://purl.org/dc/elements/1.1/}language')
        language.text = 'en'

        # Modified date (required for EPUB 3.0)
        modified = etree.SubElement(metadata_elem, 'meta', property='dcterms:modified')
        modified.text = datetime.now().isoformat() + 'Z'

        # Fixed-layout properties (required for Apple Books)
        etree.SubElement(metadata_elem, 'meta', property='rendition:layout').text = 'pre-paginated'
        etree.SubElement(metadata_elem, 'meta', property='rendition:orientation').text = 'portrait'
        etree.SubElement(metadata_elem, 'meta', property='rendition:spread').text = 'none'

        # Viewport size
        first_page = pages_content[0]
        viewport = etree.SubElement(
            metadata_elem,
            'meta',
            property='rendition:viewport',
            content=f'width={first_page.page_width},height={first_page.page_height}'
        )

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

        # Add nav document (required for EPUB 3.0)
        etree.SubElement(
            manifest,
            'item',
            {
                'id': 'nav',
                'href': 'nav.xhtml',
                'media-type': 'application/xhtml+xml',
                'properties': 'nav'
            }
        )

        # Add page documents
        for page in pages_content:
            attrs = {
                'id': f'page{page.page_num}',
                'href': f'page{page.page_num:03d}.xhtml',
                'media-type': 'application/xhtml+xml'
            }
            etree.SubElement(manifest, 'item', attrs)

        # Add images to manifest
        image_files = set()
        for page in pages_content:
            for img in page.image_elements:
                image_files.add(img.image_path)

        for img_file in image_files:
            # All images are PNG
            mime_type = 'image/png'

            etree.SubElement(
                manifest,
                'item',
                {
                    'id': f'image_{img_file.replace("/", "_").replace(".", "_")}',
                    'href': f'images/{img_file}',
                    'media-type': mime_type
                }
            )

        # Spine (reading order)
        spine = etree.SubElement(package, 'spine')
        for page in pages_content:
            etree.SubElement(
                spine,
                'itemref',
                {'idref': f'page{page.page_num}'}
            )

        # Write to file
        opf_file = self.oebps_dir / "content.opf"
        with open(opf_file, 'wb') as f:
            f.write(etree.tostring(package, xml_declaration=True, encoding='UTF-8', pretty_print=True))

    def _create_toc_ncx(self, pages_content: List[PageContent]):
        """Create OEBPS/toc.ncx (for backward compatibility)"""
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

    def _create_nav_xhtml(self, pages_content: List[PageContent]):
        """Create OEBPS/nav.xhtml (required for EPUB 3.0)"""
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
        title = etree.SubElement(head, 'title')
        title.text = 'Navigation'
        link = etree.SubElement(head, 'link', rel='stylesheet', href='styles.css', type='text/css')

        # Body
        body = etree.SubElement(html, 'body')

        # Navigation list
        nav = etree.SubElement(body, '{http://www.idpf.org/2007/ops}nav', id='toc')
        h1 = etree.SubElement(nav, 'h1')
        h1.text = 'Table of Contents'

        ol = etree.SubElement(nav, 'ol')
        for page in pages_content:
            li = etree.SubElement(ol, 'li')
            a = etree.SubElement(li, 'a', href=f'page{page.page_num:03d}.xhtml')
            a.text = f'Page {page.page_num}'

        # Write to file
        nav_file = self.oebps_dir / "nav.xhtml"
        with open(nav_file, 'wb') as f:
            f.write(etree.tostring(html, xml_declaration=True, encoding='UTF-8', pretty_print=True))

    def _create_page_xhtml_files(self, pages_content: List[PageContent]):
        """Create individual XHTML files for each page"""
        for page in pages_content:
            xhtml = self._generate_page_xhtml(page)
            xhtml_file = self.oebps_dir / f"page{page.page_num:03d}.xhtml"

            with open(xhtml_file, 'wb') as f:
                f.write(etree.tostring(xhtml, xml_declaration=True, encoding='UTF-8', pretty_print=True))

    def _generate_page_xhtml(self, page: PageContent) -> etree._Element:
        """Generate XHTML for a single page using SVG wrapper for better compatibility"""
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
        meta_viewport = etree.SubElement(
            head,
            'meta',
            name='viewport',
            content=f'width={int(page.page_width)}, height={int(page.page_height)}'
        )
        title = etree.SubElement(head, 'title')
        title.text = f'Page {page.page_num}'
        link = etree.SubElement(head, 'link', rel='stylesheet', href='styles.css', type='text/css')

        # Body with page container (like InDesign EPUB)
        body = etree.SubElement(html, 'body', style=f'width:{int(page.page_width)}px;height:{int(page.page_height)}px')

        # Add images as HTML img tags in divs (matches InDesign approach)
        # This preserves image quality better than SVG
        for img_idx, img in enumerate(page.image_elements):
            img_div = etree.SubElement(
                body,
                'div',
                {
                    'class': 'Basic-Graphics-Frame',
                    'style': f'position:absolute;left:{img.x0:.1f}px;top:{img.y0:.1f}px;width:{img.width:.1f}px;height:{img.height:.1f}px'
                }
            )
            etree.SubElement(
                img_div,
                'img',
                {
                    'src': f'images/{img.image_path}',
                    'style': 'width:100%;height:100%;',
                    'alt': ''
                }
            )

        # Add text as HTML elements
        for text_idx, text in enumerate(page.text_elements):
            text_div = etree.SubElement(
                body,
                'div',
                {
                    'class': 'Basic-Text-Frame',
                    'style': f'position:absolute;left:{text.x0:.1f}px;top:{text.y0:.1f}px'
                }
            )
            text_p = etree.SubElement(text_div, 'p')
            text_span = etree.SubElement(text_p, 'span')

            text_span.text = text.text

            # Apply text styling
            style_parts = [
                f'font-size:{text.font_size:.1f}px',
                f'line-height:{text.line_height:.1f}px',
                'font-family:serif',
                'color:black'
            ]
            if text.is_bold:
                style_parts.append('font-weight:bold')
            if text.is_italic:
                style_parts.append('font-style:italic')

            text_span.set('style', ';'.join(style_parts))

        return html

    def _create_stylesheet(self):
        """Create OEBPS/styles.css"""
        css_content = """/* Fixed-Layout EPUB Stylesheet - Apple Books Compatible - HTML Version */

* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

html, body {
    width: 100%;
    height: 100%;
    margin: 0;
    padding: 0;
    overflow: hidden;
}

body {
    background-color: #ffffff;
    position: relative;
    page-break-after: always;
}

/* Graphics frame - images */
.Basic-Graphics-Frame {
    overflow: hidden;
}

.Basic-Graphics-Frame img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
}

/* Text frame */
.Basic-Text-Frame {
    overflow: visible;
}

.Basic-Text-Frame p {
    margin: 0;
    padding: 0;
    line-height: 1;
}

.Basic-Text-Frame span {
    white-space: nowrap;
}

/* Ensure proper text rendering */
@supports (text-size-adjust: 100%) {
    html {
        -webkit-text-size-adjust: 100%;
        -moz-text-size-adjust: 100%;
        text-size-adjust: 100%;
    }
}
"""

        css_file = self.oebps_dir / "styles.css"
        with open(css_file, 'w', encoding='utf-8') as f:
            f.write(css_content)

    def _package_epub(self):
        """Package the EPUB directory into a ZIP file"""
        # Create output directory if needed
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        # Create EPUB ZIP file
        with ZipFile(str(self.output_path), 'w', ZIP_DEFLATED) as epub:
            # Add mimetype first (uncompressed and stored first)
            mimetype_file = self.epub_root / "mimetype"

            # Read the exact mimetype content
            with open(mimetype_file, 'rb') as f:
                mimetype_content = f.read()

            # Write it uncompressed as the first file
            epub.writestr('mimetype', mimetype_content, compress_type=0)

            # Add all other files with compression
            for root, dirs, files in os.walk(str(self.epub_root)):
                for file in files:
                    if file == "mimetype":
                        continue

                    file_path = Path(root) / file
                    arcname = file_path.relative_to(self.epub_root)
                    epub.write(file_path, arcname=arcname)

        # Cleanup temp directory
        shutil.rmtree(self.epub_root)
