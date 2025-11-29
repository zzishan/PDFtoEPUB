"""
PDF Extractor - Extracts content from PDF with precise positioning information
Preserves exact layout through absolute positioning coordinates
"""

import pdfplumber
import os
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from PIL import Image, ImageEnhance
import numpy as np
import io
import json
from tqdm import tqdm


@dataclass
class TextElement:
    """Represents a text element with positioning info"""
    text: str
    x0: float  # Left position
    y0: float  # Top position
    x1: float  # Right position
    y1: float  # Bottom position
    font_name: str
    font_size: float
    is_bold: bool
    is_italic: bool
    line_height: float
    page_num: int


@dataclass
class ImageElement:
    """Represents an image element with positioning info"""
    image_path: str
    x0: float
    y0: float
    x1: float
    y1: float
    width: float
    height: float
    page_num: int


@dataclass
class PageContent:
    """Represents all content on a single page"""
    page_num: int
    page_width: float
    page_height: float
    text_elements: List[TextElement]
    image_elements: List[ImageElement]
    background_image_path: str = None


class PDFExtractor:
    """Extracts content from PDF with positioning preservation"""

    def __init__(self, pdf_path: str, output_dir: str = "extracted"):
        self.pdf_path = pdf_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir = self.output_dir / "images"
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir = self.output_dir / "metadata"
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def extract_all(self) -> Tuple[List[PageContent], Dict[str, Any]]:
        """Extract all content from PDF"""
        pages_content = []
        metadata = {}

        with pdfplumber.open(self.pdf_path) as pdf:
            metadata['total_pages'] = len(pdf.pages)
            metadata['title'] = pdf.metadata.get('Title', 'Unknown')
            metadata['author'] = pdf.metadata.get('Author', 'Unknown')

            print(f"Extracting from {len(pdf.pages)} pages...")

            for page_num, page in enumerate(tqdm(pdf.pages, desc="Extracting pages"), 1):
                page_content = self._extract_page(page, page_num)
                pages_content.append(page_content)

        # Save metadata
        self._save_metadata(metadata, pages_content)

        return pages_content, metadata

    def _extract_page(self, page: pdfplumber.PDF.pages, page_num: int) -> PageContent:
        """Extract content from a single page"""
        page_content = PageContent(
            page_num=page_num,
            page_width=page.width,
            page_height=page.height,
            text_elements=[],
            image_elements=[]
        )

        # Extract text with layout
        text_elements = self._extract_text(page, page_num)
        page_content.text_elements = text_elements

        # Extract images
        image_elements = self._extract_images(page, page_num)
        page_content.image_elements = image_elements

        # Generate background image of the page (for reference)
        bg_image_path = self._save_page_image(page, page_num)
        page_content.background_image_path = bg_image_path

        return page_content

    def _extract_text(self, page: pdfplumber.PDF.pages, page_num: int) -> List[TextElement]:
        """Extract text elements with positioning"""
        text_elements = []
        page_height = page.height

        # Get chars for detailed positioning
        chars = page.chars

        # Group chars into lines (by y-coordinate proximity)
        lines = {}
        for char in chars:
            y = round(char['y0'], 1)
            if y not in lines:
                lines[y] = []
            lines[y].append(char)

        # Process each line
        for y_key in sorted(lines.keys()):
            line_chars = sorted(lines[y_key], key=lambda c: c['x0'])

            # Group into words and extract positioning
            line_text = ''.join([c['text'] for c in line_chars])

            if line_text.strip():
                x0 = line_chars[0]['x0']
                y0 = line_chars[0]['y0']
                x1 = line_chars[-1]['x1']
                y1 = line_chars[-1]['y1']

                # Convert PDF coordinates (origin at bottom-left) to HTML coordinates (origin at top-left)
                # y0_html = page_height - y1 (use y1 because y0 is top of text, y1 is bottom)
                y0_html = page_height - y1
                y1_html = page_height - y0

                # Get font info from first char
                font_name = line_chars[0].get('font', 'Unknown')
                font_size = line_chars[0].get('size', 12)

                text_elem = TextElement(
                    text=line_text,
                    x0=x0,
                    y0=y0_html,
                    x1=x1,
                    y1=y1_html,
                    font_name=font_name,
                    font_size=font_size,
                    is_bold='Bold' in font_name,
                    is_italic='Italic' in font_name or 'Oblique' in font_name,
                    line_height=y1_html - y0_html,
                    page_num=page_num
                )
                text_elements.append(text_elem)

        return text_elements

    def _extract_images(self, page: pdfplumber.PDF.pages, page_num: int) -> List[ImageElement]:
        """Extract images with positioning"""
        image_elements = []
        page_height = page.height

        # Extract images from page
        for img_index, img in enumerate(page.images):
            try:
                # Get image binary
                image_bytes = img['stream'].get_rawdata()

                # Create PIL image
                image_data = Image.open(io.BytesIO(image_bytes))

                # Convert image to RGB if needed
                if image_data.mode == 'CMYK':
                    # Use inverted CMYK conversion with reduced saturation
                    image_data = self._cmyk_to_rgb_balanced(image_data)
                elif image_data.mode in ('LA', 'PA'):
                    # Handle other modes with alpha channel
                    image_data = image_data.convert('RGBA')
                elif image_data.mode == '1':
                    # Binary/monochrome
                    image_data = image_data.convert('RGB')

                # Save as PNG (lossless, matches InDesign approach)
                img_filename = f"page_{page_num:03d}_img_{img_index:02d}.png"
                img_path = self.images_dir / img_filename

                # Save PNG without compression - let ZIP handle it
                # This preserves maximum quality
                image_data.save(img_path, 'PNG', compress_level=0, optimize=False)

                # Convert PDF coordinates (origin at bottom-left) to HTML coordinates (origin at top-left)
                # In PDF: y0 is top of image, y1 is bottom
                # In HTML: we want top position = page_height - y1 (image's bottom becomes distance from top)
                y0_html = page_height - img['y1']
                y1_html = page_height - img['y0']
                height_html = y1_html - y0_html

                # Create element
                img_elem = ImageElement(
                    image_path=img_filename,
                    x0=img['x0'],
                    y0=y0_html,
                    x1=img['x1'],
                    y1=y1_html,
                    width=img['x1'] - img['x0'],
                    height=height_html,
                    page_num=page_num
                )
                image_elements.append(img_elem)
            except Exception as e:
                print(f"Warning: Could not extract image on page {page_num}: {e}")

        return image_elements

    def _cmyk_to_rgb_balanced(self, image: Image.Image) -> Image.Image:
        """Convert CMYK to RGB with inverted formula and reduced saturation for balanced colors"""
        if image.mode != 'CMYK':
            return image

        try:
            # Convert image data to numpy array
            cmyk_data = np.array(image, dtype=np.float32)

            # Inverted CMYK conversion (this PDF uses inverted encoding)
            c = (255.0 - cmyk_data[:, :, 0]) / 255.0
            m = (255.0 - cmyk_data[:, :, 1]) / 255.0
            y = (255.0 - cmyk_data[:, :, 2]) / 255.0
            k = (255.0 - cmyk_data[:, :, 3]) / 255.0

            # Apply CMYK to RGB conversion formula
            r = 255 * (1 - c) * (1 - k)
            g = 255 * (1 - m) * (1 - k)
            b = 255 * (1 - y) * (1 - k)

            # Combine into RGB image
            rgb_data = np.stack([r, g, b], axis=2).astype(np.uint8)
            rgb_image = Image.fromarray(rgb_data, 'RGB')

            # Reduce saturation to match PDF colors (inverted formula oversaturates)
            enhancer = ImageEnhance.Color(rgb_image)
            rgb_image = enhancer.enhance(0.75)  # 75% saturation (25% reduction)

            return rgb_image
        except Exception as e:
            print(f"Warning: Could not convert CMYK to RGB: {e}")
            # Fallback to PIL's default conversion
            return image.convert('RGB')

    def _save_page_image(self, page: pdfplumber.PDF.pages, page_num: int) -> str:
        """Save a rendered image of the entire page for reference"""
        try:
            # Render page as image at higher resolution for better quality
            page_image = page.to_image(resolution=150)  # 150 DPI for better quality reference

            # Convert to RGB if needed
            if page_image.mode not in ('RGB', 'L', 'RGBA'):
                page_image = page_image.convert('RGB')

            img_filename = f"page_{page_num:03d}_reference.png"
            img_path = self.images_dir / img_filename

            # Save PNG without compression
            page_image.save(img_path, 'PNG', compress_level=0, optimize=False)

            return img_filename
        except Exception as e:
            print(f"Warning: Could not save page image for page {page_num}: {e}")
            return None

    def _save_metadata(self, metadata: Dict, pages_content: List[PageContent]):
        """Save extraction metadata for debugging and validation"""
        metadata_file = self.metadata_dir / "extraction_metadata.json"

        # Prepare metadata for JSON serialization
        pages_info = []
        for page in pages_content:
            page_info = {
                'page_num': page.page_num,
                'page_width': page.page_width,
                'page_height': page.page_height,
                'text_elements_count': len(page.text_elements),
                'image_elements_count': len(page.image_elements),
                'background_image': page.background_image_path
            }
            pages_info.append(page_info)

        metadata['pages'] = pages_info

        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"Metadata saved to {metadata_file}")
