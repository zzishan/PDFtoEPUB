#!/usr/bin/env python3
"""
PDFtoEPUB Command Line Interface
Main entry point for PDF to EPUB conversion
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.converter import PDFtoEPUBConverter


def main():
    parser = argparse.ArgumentParser(
        description='Convert PDF to fixed-layout EPUB with 100% format preservation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python convert.py Sample.pdf
  python convert.py Sample.pdf -o output.epub
  python convert.py Sample.pdf -o output.epub --no-validate
        """
    )

    parser.add_argument(
        'pdf_file',
        help='Input PDF file path'
    )

    parser.add_argument(
        '-o', '--output',
        help='Output EPUB file path (default: input filename with .epub extension)',
        default=None
    )

    parser.add_argument(
        '--no-validate',
        action='store_true',
        help='Skip validation after conversion'
    )

    parser.add_argument(
        '-w', '--working-dir',
        default='conversion_work',
        help='Working directory for temporary files (default: conversion_work)'
    )

    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    # Validate input file
    pdf_file = Path(args.pdf_file)
    if not pdf_file.exists():
        print(f"Error: PDF file not found: {args.pdf_file}", file=sys.stderr)
        sys.exit(1)

    # Determine output path
    output_path = args.output if args.output else pdf_file.with_suffix('.epub')

    try:
        # Create converter
        converter = PDFtoEPUBConverter(
            pdf_path=str(pdf_file),
            output_epub_path=str(output_path),
            working_dir=args.working_dir
        )

        # Run conversion
        print(f"Converting: {pdf_file}")
        print(f"Output: {output_path}")

        result = converter.convert(validate=not args.no_validate)

        # Print summary
        summary = converter.get_summary()
        print("\n" + "="*50)
        print("CONVERSION COMPLETE")
        print("="*50)
        print(f"Input PDF: {summary['input_pdf']}")
        print(f"Output EPUB: {summary['output_epub']}")
        print(f"Output size: {summary['output_size_mb']:.2f} MB")
        print("="*50 + "\n")

        sys.exit(0)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
