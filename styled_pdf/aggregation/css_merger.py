"""CSS deduplication and merging across pages."""

from __future__ import annotations

import re
from collections import Counter


def _extract_rules(css: str) -> list[str]:
    """Extract individual CSS rule blocks from a stylesheet string."""
    # Match selector { declarations }
    pattern = re.compile(r"([^{}]+)\{([^{}]*)\}", re.DOTALL)
    return [m.group(0).strip() for m in pattern.finditer(css)]


def _extract_declarations(css: str) -> dict[str, str]:
    """Return {selector: declarations_block} mapping."""
    pattern = re.compile(r"([^{}]+)\{([^{}]*)\}", re.DOTALL)
    result: dict[str, str] = {}
    for m in pattern.finditer(css):
        selector = m.group(1).strip()
        declarations = m.group(2).strip()
        if selector in result:
            result[selector] += "\n  " + declarations
        else:
            result[selector] = declarations
    return result


def _extract_color_values(css_blocks: list[str]) -> list[str]:
    """Find hex color values appearing 3+ times across all CSS."""
    hex_pattern = re.compile(r"#[0-9a-fA-F]{3,6}\b")
    counts: Counter[str] = Counter()
    for block in css_blocks:
        for color in hex_pattern.findall(block):
            counts[color.lower()] += 1
    return [color for color, count in counts.items() if count >= 3]


def _extract_font_families(css_blocks: list[str]) -> list[str]:
    """Find font-family values appearing 2+ times across all CSS."""
    font_pattern = re.compile(r"font-family\s*:\s*([^;]+);")
    counts: Counter[str] = Counter()
    for block in css_blocks:
        for font in font_pattern.findall(block):
            counts[font.strip()] += 1
    return [font for font, count in counts.items() if count >= 2]


def merge_css(page_css_list: list[str]) -> str:
    """Merge per-page CSS into a single stylesheet.

    - Extracts recurring colors/fonts into CSS custom properties on :root
    - Deduplicates identical rules
    - Returns the merged CSS string
    """
    if not page_css_list:
        return ""

    all_css = "\n".join(page_css_list)

    # Collect recurring colors and fonts for custom properties
    colors = _extract_color_values(page_css_list)
    fonts = _extract_font_families(page_css_list)

    root_vars: list[str] = []
    color_replacements: dict[str, str] = {}
    font_replacements: dict[str, str] = {}

    for i, color in enumerate(colors, 1):
        var_name = f"--color-{i}"
        root_vars.append(f"  {var_name}: {color};")
        color_replacements[color] = f"var({var_name})"

    for i, font in enumerate(fonts, 1):
        var_name = f"--font-{i}"
        root_vars.append(f"  {var_name}: {font};")
        font_replacements[font] = f"var({var_name})"

    # Apply replacements to merged CSS
    merged = all_css
    for orig, var in color_replacements.items():
        merged = re.sub(re.escape(orig), var, merged, flags=re.IGNORECASE)
    for orig, var in font_replacements.items():
        merged = merged.replace(orig, var)

    # Deduplicate identical rule blocks (exact match)
    seen: set[str] = set()
    deduped_rules: list[str] = []
    for rule in _extract_rules(merged):
        normalized = re.sub(r"\s+", " ", rule).strip()
        if normalized not in seen:
            seen.add(normalized)
            deduped_rules.append(rule)

    # Assemble final CSS
    parts: list[str] = []

    if root_vars:
        parts.append(":root {\n" + "\n".join(root_vars) + "\n}\n")

    parts.append("\n".join(deduped_rules))

    return "\n\n".join(parts)
