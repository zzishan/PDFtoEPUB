# Quick Start Guide - PDFtoEPUB

Get up and running in 5 minutes!

## Installation (One-time setup)

```bash
cd /Users/zishan/PDFtoEPUB
pip install -r requirements.txt
```

Takes about 2-3 minutes depending on internet speed.

## Basic Usage

### Convert a PDF to EPUB
```bash
python3 convert.py your_file.pdf
```

This creates `your_file.epub` in the same directory.

### Get the output in a specific location
```bash
python3 convert.py your_file.pdf -o output_folder/my_ebook.epub
```

### Show detailed progress
```bash
python3 convert.py your_file.pdf -v
```

### Skip validation (faster)
```bash
python3 convert.py your_file.pdf --no-validate
```

## Examples

**Example 1: Simple conversion**
```bash
python3 convert.py Sample.pdf
# Creates: Sample.epub
```

**Example 2: With custom output**
```bash
python3 convert.py art_book.pdf -o books/art_book.epub
# Creates: books/art_book.epub
```

**Example 3: Batch conversion**
```bash
for pdf in *.pdf; do
  python3 convert.py "$pdf"
done
# Converts all PDFs in current directory
```

## What Gets Generated

After conversion, you'll have:

1. **output.epub** - Your converted ebook (ready to use!)
2. **conversion_work/** - Temporary files including:
   - `extracted/images/` - All extracted images
   - `validation_report.json` - Quality check results

## Validation Check

To verify the conversion was successful:

```bash
cat conversion_work/validation_report.json | python3 -m json.tool
```

Look for: `"overall_status": true` ✓

## Troubleshooting Quick Fixes

| Problem | Solution |
|---------|----------|
| Command not found: convert.py | Make sure you're in the PDFtoEPUB directory |
| ModuleNotFoundError | Run `pip install -r requirements.txt` |
| File takes too long | This is normal for large PDFs (10+ MB) |
| EPUB won't open | Check validation_report.json for issues |

## What's Preserved

✓ All text content
✓ All images and colors
✓ Text positioning and layout
✓ Font sizes and styles
✓ Page structure

## File Size Reference

- Input PDF: 18 MB → Output EPUB: 23 MB (size varies by content)
- Processing time: ~5 seconds per 18 MB

## Using the EPUB

The generated EPUB file can be opened in:
- **Kindle**: Copy to your Kindle device
- **iBooks**: Open directly in Apple Books
- **Google Play Books**: Upload to your library
- **Calibre**: Convert to other formats if needed
- **Web Readers**: Use any EPUB-compatible online reader

## Advanced Options

```bash
python3 convert.py input.pdf \
  -o output.epub \
  -v \
  -w temp_dir/
```

- `-o`: Output file path
- `-v`: Verbose (show details)
- `-w`: Working directory for temp files
- `--no-validate`: Skip validation

## Full Help

```bash
python3 convert.py --help
```

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Check [config/config.json](config/config.json) for advanced settings
- View extraction results in `conversion_work/extracted/metadata/`

## Typical Workflow

```bash
# 1. Place your PDF in the project directory
cp ~/Downloads/mybook.pdf .

# 2. Convert it
python3 convert.py mybook.pdf -v

# 3. Check the validation
cat conversion_work/validation_report.json | python3 -m json.tool

# 4. Use your EPUB
# The file is ready in: mybook.epub
```

## Tips

- For best results, ensure your PDF is not corrupted or encrypted
- Large PDFs (100+ MB) may take longer to process
- The tool automatically handles CMYK images (common in print PDFs)
- Each conversion is independent; you can run multiple conversions

---

**That's it!** You now have a professional EPUB conversion tool ready to use.

For more detailed information, see [README.md](README.md)
