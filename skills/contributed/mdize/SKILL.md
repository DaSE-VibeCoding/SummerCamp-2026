---
name: mdize
description: Convert PDFs, Word documents, PowerPoint files, and images into Markdown with extracted images through MinerU. Use when a user asks to turn local documents into Markdown, extract readable content from course materials or papers, or OCR supported images. Do not use for HTML unless the user explicitly requests MinerU-based HTML conversion.
---

# mdize

Convert documents into Markdown and extracted images. Prefer local MinerU for PDFs when it is installed; use the bundled API script for supported files when local processing is unavailable or unsuitable.

## Supported input

- PDF, DOC/DOCX, PPT/PPTX
- PNG, JPG, JPEG (OCR)
- HTML only when the user explicitly requests MinerU for HTML

## Choose a mode

1. Run `command -v mineru`. If it exists and the input is PDF, prefer local MinerU: it does not need a Token or network connection.
2. For other supported formats, or when local MinerU is unavailable, use `scripts/mineru_batch_convert.py`.
3. The API script sends files to MinerU. Do not use it for documents that must remain local.

## Local PDF conversion

```bash
mineru -p "/path/to/document.pdf" -o "/tmp/mdize-output" --backend pipeline
```

Move the resulting Markdown and `images/` directory to a nearby `_md/` directory after confirming the output.

## API conversion

Install the only Python dependency and provide your own Token without writing it into a file:

```bash
python -m pip install requests
export MINERU_API_TOKEN="your-token"
python scripts/mineru_batch_convert.py "/path/to/paper.pdf"
```

Pass multiple files or a directory to batch them:

```bash
python scripts/mineru_batch_convert.py "/path/to/slides.pptx" "/path/to/reports"
```

The default output directory is `_md/` next to the first input file. Override it with `--output`.

## Validate and report

After conversion, check that the output contains Markdown and extracted images. Report the output path, converted file count, and any failed files. Complex layouts, scanned documents, formulas, and tables may need manual review.

## Security

- Never commit, paste, or log `MINERU_API_TOKEN`.
- Use local MinerU for sensitive PDFs whenever possible.
- The API script is for supported local files only; it does not fetch arbitrary URLs.
