# styled-pdf

Extract semantic HTML and CSS from styled PDFs using Claude's vision AI. Supports both text-based PDFs (with embedded font/layout metadata) and scanned/image-based PDFs (OCR handled by Claude).

## How it works

1. **Extract** — PyMuPDF reads text blocks, font names, sizes, colors, and page dimensions from the PDF
2. **Render** — Each page is rendered to a PNG image (via pdf2image/poppler)
3. **Detect** — Pages with sparse text are flagged as scanned; Claude's vision handles OCR automatically
4. **Analyze** — Each page image + metadata is sent to Claude, which returns a JSON payload with `html`, `css`, and `style_tokens`
5. **Aggregate** — Per-page CSS is deduplicated, recurring colors/fonts are promoted to CSS custom properties, and pages are assembled into a single HTML document

## Prerequisites

**System dependency (required for PDF rendering):**

```bash
# macOS
brew install poppler

# Ubuntu/Debian
sudo apt-get install poppler-utils

# Windows — download from https://github.com/oschwartz10612/poppler-windows/releases
```

**Anthropic API key:** Get one at [console.anthropic.com](https://console.anthropic.com).

## Installation

```bash
# Clone the repo
git clone <repo-url>
cd styled-pdf

# Install with pip (Python 3.11+)
pip install -e .

# Or with uv
uv sync
```

Copy `.env.example` to `.env` and add your API key:

```bash
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY=your_key_here
```

## Basic usage

```bash
styled-pdf document.pdf
```

Produces `document.html` in the same directory with all styles inlined in a `<style>` block.

## CLI reference

```text
styled-pdf PDF_FILE [options]
```

| Option                  | Default              | Description                                               |
| ----------------------- | -------------------- | --------------------------------------------------------- |
| `-o, --output PATH`     | `<input>.html`       | Output HTML file path                                     |
| `--external-css`        | off                  | Write CSS to a separate `.css` file, not inline `<style>` |
| `--pages RANGE`         | all                  | Page range: `1-5`, `2,4,7`, or `3-5,8`                   |
| `--dpi INTEGER`         | `150`                | Render DPI. Higher = more accurate, larger API payload    |
| `--concurrency INTEGER` | `3`                  | Max simultaneous Claude API calls                         |
| `--model TEXT`          | `claude-sonnet-4-6`  | Claude model ID to use                                    |
| `--max-tokens INTEGER`  | `4096`               | Max tokens per page response                              |
| `--api-key TEXT`        | env var              | Anthropic API key (overrides `ANTHROPIC_API_KEY`)         |
| `--debug`               | off                  | Save page images and raw responses to `./debug/`          |
| `--quiet`               | off                  | Suppress progress output                                  |

## Examples

**Process specific pages:**

```bash
styled-pdf report.pdf --pages 1-10
```

**Save CSS separately:**

```bash
styled-pdf report.pdf --external-css
# produces report.html + report.css
```

**Higher quality render for small text:**

```bash
styled-pdf report.pdf --dpi 200
```

**Debug mode — inspect what Claude sees and returns:**

```bash
styled-pdf report.pdf --debug
# saves debug/page_N_image.png and debug/page_N_response.json
```

**Specify output path and API key explicitly:**

```bash
styled-pdf report.pdf -o output/index.html --api-key sk-ant-...
```

**Process a scanned document (OCR handled automatically):**

```bash
styled-pdf scanned-invoice.pdf --dpi 200
```

**Limit concurrency (e.g. to stay within rate limits):**

```bash
styled-pdf large-doc.pdf --concurrency 1
```

## Features

### Semantic HTML output

Claude produces proper semantic markup — `<h1>`–`<h6>`, `<p>`, `<ul>`, `<ol>`, `<table>`, `<figure>`, `<aside>`, `<header>`, `<footer>` — rather than `<div>`-soup. Data tables use `<thead>`/`<tbody>`/`<th>` structure. Multi-column layouts use CSS Grid or Flexbox.

### OCR for scanned PDFs

Pages with fewer than 50 extracted characters are automatically flagged as scanned. Claude's vision model reads the text directly from the image — no separate OCR tool (Tesseract etc.) is required.

### Cross-page style consistency

Page 1 is analyzed first. Its `style_tokens` (detected fonts, colors, heading class names) are injected into the prompts for all subsequent pages, so Claude reuses the same CSS class names and design system throughout the document.

### CSS custom properties

Colors and font families that appear on 3+ pages are automatically promoted to CSS custom properties on `:root`:

```css
:root {
  --color-1: #1a2b3c;
  --font-1: 'Helvetica Neue', sans-serif;
}
```

### CSS deduplication

Identical CSS rules across pages are deduplicated. The final stylesheet contains each unique rule once.

### Concurrent processing

Pages 2..N are processed in parallel (default: 3 at a time) using async Claude API calls, significantly reducing total processing time for multi-page documents.

### Debug artifacts

With `--debug`, the tool saves:

- `debug/page_N_image.png` — the rendered page image sent to Claude
- `debug/page_N_response.json` — the raw JSON response from Claude (html, css, style_tokens)

Useful for tuning DPI, inspecting extraction quality, or diagnosing issues.

## Output structure

The generated HTML wraps each page in a `<div class="page page-N">` element:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>document</title>
  <style>
    :root { --color-1: #1a2b3c; }
    .page { ... }
    .page-1 h1 { ... }
  </style>
</head>
<body class="pdf-document">
  <div class="page page-1">...</div>
  <div class="page page-2">...</div>
</body>
</html>
```

## Environment variables

| Variable             | Description            |
| -------------------- | ---------------------- |
| `ANTHROPIC_API_KEY`  | Your Anthropic API key |
