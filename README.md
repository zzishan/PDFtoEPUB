# PDFtoEPUB: PDF to Fixed-Layout EPUB Converter

Professional PDF to EPUB conversion tool with 100% format preservation and exact layout retention for art books, textbooks, and documents with complex designs.

## Features

- **100% Format Preservation**: Maintains exact positioning of text and images from the source PDF
- **Fixed-Layout EPUB**: Generates EPUB files that preserve the original page layout on all devices
- **Precise Positioning**: Uses CSS absolute positioning to replicate exact text and image placement
- **Image Preservation**: Extracts and preserves all images with automatic format conversion (CMYK → RGB)
- **Text Extraction**: Preserves all text content with font information (size, style, bold/italic)
- **Validation**: Built-in integrity checking to ensure data completeness
- **Metadata Preservation**: Maintains PDF metadata and document information

## Project Structure

```
PDFtoEPUB/
├── Sample.pdf                 # Example PDF file
├── convert.py                 # Main CLI tool
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── config/
│   └── config.json           # Configuration settings
├── src/
│   ├── __init__.py           # Package initialization
│   ├── converter.py          # Main conversion pipeline
│   ├── pdf_extractor.py      # PDF content extraction
│   ├── epub_generator.py     # EPUB file generation
│   └── validator.py          # Content validation
├── output/                    # Generated EPUB files
└── conversion_work/           # Temporary extraction files
    ├── extracted/
    │   ├── images/           # Extracted images
    │   └── metadata/         # Extraction metadata
    └── validation_report.json # Validation results
```

## Installation

### Prerequisites
- Python 3.10+
- pip package manager

### Setup

1. **Clone/Navigate to the project directory**
```bash
cd /Users/zishan/PDFtoEPUB
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

The following Python packages will be installed:
- `pdfplumber` - Advanced PDF text and image extraction
- `Pillow` - Image processing and format conversion
- `lxml` - XML/EPUB file generation
- `ebooklib` - EPUB utilities
- `tqdm` - Progress bars
- And others for validation and utilities

## Usage

### Basic Conversion

```bash
python3 convert.py <input_pdf_file>
```

This will create an EPUB file with the same name as the input PDF:
```bash
python3 convert.py Sample.pdf
# Creates: Sample.epub
```

### Custom Output Path

```bash
python3 convert.py Sample.pdf -o my_output.epub
```

### Skip Validation

For faster conversion without integrity checking:
```bash
python3 convert.py Sample.pdf --no-validate
```

### Verbose Output

For detailed conversion progress:
```bash
python3 convert.py Sample.pdf -v
```

### Custom Working Directory

Specify where temporary files are stored:
```bash
python3 convert.py Sample.pdf -w /tmp/conversion
```

## How It Works

### Step 1: PDF Extraction
The converter extracts content from the PDF with precise positioning information:
- **Text Elements**: Position (x0, y0, x1, y1), font name, size, and styling
- **Images**: Position, dimensions, and binary content
- **Page Dimensions**: Width and height of each page
- **Metadata**: Title, author, page count

### Step 2: EPUB Structure Generation
Creates a valid EPUB 3.0 file with fixed-layout rendering:
- **Fixed Layout**: `rendition:layout = "pre-paginated"`
- **Orientation**: Set to portrait mode
- **Absolute Positioning**: CSS absolute positioning for exact layout
- **OPF Package**: Proper manifest, spine, and metadata

### Step 3: Content Placement
Each page is rendered as XHTML with:
- **Page Container**: Fixed dimensions matching original PDF page size
- **Absolute Elements**: All text and images positioned with pixel-perfect accuracy
- **CSS Styling**: Font sizes, weights, styles applied from extracted metadata

### Step 4: Validation
Integrity checks to ensure:
- ✓ All pages are present
- ✓ All images are preserved
- ✓ Text content is complete
- ✓ EPUB structure is valid
- ✓ XML files are well-formed

## Output

### EPUB File Structure
```
Sample.epub
├── mimetype (uncompressed)
├── META-INF/
│   └── container.xml
└── OEBPS/
    ├── content.opf (package metadata)
    ├── toc.ncx (table of contents)
    ├── styles.css (stylesheet)
    ├── page001.xhtml through page00N.xhtml
    └── images/
        ├── page_001_img_00.png
        ├── page_001_img_01.png
        └── ... (all extracted images)
```

### Validation Report
After each conversion, a detailed validation report is generated:
```
conversion_work/validation_report.json
```

Contains checks for:
- File existence and sizes
- EPUB structure validity
- Page count matching
- Image preservation count
- Text content verification
- XML validity

## Configuration

Edit `config/config.json` to customize conversion behavior:

```json
{
  "conversion": {
    "dpi": 96,                    // DPI for page rendering
    "preserve_layout": true,      // Preserve exact layout
    "fixed_layout_epub": true,    // Use fixed-layout EPUB
    "extract_images": true,       // Extract images
    "extract_text": true          // Extract text
  },
  "epub": {
    "language": "en",
    "creator": "PDFtoEPUB Converter"
  }
}
```

## Performance Notes

- **Processing Time**: Depends on PDF size and complexity (typically 5-20 seconds per 18MB file)
- **Output Size**: EPUB files are typically 10-20% larger than source PDF due to uncompressed XML
- **Memory Usage**: Requires enough memory to hold extracted images (multiple large images)
- **Image Handling**: CMYK images are automatically converted to RGB for compatibility

## Supported Features

### Text Features
- ✓ Font names and sizes
- ✓ Bold and italic styling
- ✓ Exact positioning and spacing
- ✓ Line heights and alignment

### Image Features
- ✓ PNG format (native)
- ✓ JPEG format (supported)
- ✓ CMYK → RGB conversion (automatic)
- ✓ Exact positioning and dimensions
- ✓ Embedded in EPUB for portability

### Layout Features
- ✓ Fixed page dimensions
- ✓ Absolute positioning
- ✓ Complex multi-column layouts
- ✓ Images overlapping text
- ✓ Decorative elements

## Limitations

- **Annotations**: PDF annotations are not converted
- **Form Fields**: Interactive form fields are not supported
- **Embedded Video**: Multimedia content is not extracted
- **JavaScript**: Dynamic PDF features are not supported
- **PDF Security**: Password-protected PDFs must be unencrypted first

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'pdfplumber'"
**Solution**: Run `pip install -r requirements.txt` from the project directory

### Issue: "CMYK image conversion failed"
**Solution**: This is handled automatically. If still failing, check disk space and Pillow installation

### Issue: "Image extraction failed"
**Cause**: PDF uses embedded image format not supported by Pillow
**Solution**: Check the validation report for details on which images failed

### Issue: "EPUB won't open in reader"
**Solution**: Check the validation report. Ensure EPUB structure is valid using `unzip -l output/file.epub`

## Python API Usage

```python
from src.converter import PDFtoEPUBConverter

# Create converter
converter = PDFtoEPUBConverter(
    pdf_path='Sample.pdf',
    output_epub_path='output.epub'
)

# Run conversion with validation
epub_path = converter.convert(validate=True)

# Get summary
summary = converter.get_summary()
print(f"Created: {summary['output_epub']}")
print(f"Size: {summary['output_size_mb']:.2f} MB")
```

## Testing

To verify the installation and test with Sample.pdf:

```bash
python3 convert.py Sample.pdf -o output/Sample.epub -v
cat conversion_work/validation_report.json | python3 -m json.tool
```

Expected output: All validation checks should pass ✓

## Advanced Topics

### Custom Image Handling
Modify `pdf_extractor.py` method `_extract_images()` to implement custom image processing

### Custom Metadata
Modify `epub_generator.py` method `_create_package_opf()` to add custom metadata

### Layout Customization
Edit `epub_generator.py` method `_create_stylesheet()` to modify CSS styling

## File Formats Supported

**Input**: PDF (1.x - 2.0)
**Output**: EPUB 3.0 (fixed-layout)
**Image Formats**: PNG, JPEG, GIF (converted to PNG)

## Requirements

- Python 3.10 or higher
- 100+ MB free disk space per conversion
- Sufficient RAM for large PDFs (2GB+ for very large documents)

## Version History

### v1.0.0 (Initial Release)
- Full PDF extraction with positioning
- Fixed-layout EPUB generation
- Image preservation and conversion
- Content validation
- CLI interface

## License

This project is provided as-is for PDF to EPUB conversion purposes.

## Support

For issues or questions:
1. Check the validation report in `conversion_work/validation_report.json`
2. Review the console output for specific error messages
3. Ensure all dependencies are properly installed
4. Check that the input PDF is not corrupted or encrypted

## Technical Details

### Positioning System
- **Absolute Coordinates**: All positions use PDF coordinate system (top-left origin)
- **CSS Pixels**: 1 CSS pixel = 1/96 inch (standard screen DPI)
- **Preservation**: Exact pixel-level positioning for layout fidelity

### EPUB Format
- **Specification**: EPUB 3.0 standard
- **Layout Mode**: Pre-paginated (fixed layout)
- **Compression**: ZIP DEFLATE compression
- **Validation**: Full IDPF compliance

### Data Flow
1. PDF → Extract content with positioning
2. Extracted data → Generate XHTML pages
3. XHTML + Images → Package into EPUB ZIP
4. EPUB → Validate and report

## Credits

Built with:
- [pdfplumber](https://github.com/jsvine/pdfplumber) - PDF extraction
- [Pillow](https://python-pillow.org/) - Image processing
- [lxml](https://lxml.de/) - XML generation
- [EPUB Specification](https://www.w3.org/publishing/epub/) - Format specification
