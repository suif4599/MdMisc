import argparse
import shutil
import re
import unicodedata
from pathlib import Path
from typing import List, Optional, Tuple

import cssutils
from fontTools.ttLib import TTFont

HOME = Path.home()
DEFAULT_EXTENSIONS_ROOT = HOME / ".vscode" / "extensions"
DEFAULT_OUTPUT = HOME / ".local" / "state" / "crossnote"

cssutils.log.setLevel("CRITICAL")


def resolve_extension_dir(
    extensions_root: Path,
    extension_pattern: str,
    explicit_extension_dir: Optional[Path] = None,
) -> Path:
    if explicit_extension_dir is not None:
        if not explicit_extension_dir.exists():
            raise FileNotFoundError(f"Extension directory not found: {explicit_extension_dir}")
        return explicit_extension_dir

    matches = sorted(extensions_root.glob(extension_pattern))
    if not matches:
        raise FileNotFoundError(
            "No extension directory matched pattern "
            f"'{extension_pattern}' under '{extensions_root}'"
        )

    # Pick the latest-looking directory by lexical order to handle version suffixes.
    return matches[-1]


def generate_print_style(
    main_css_path,
    codeblock_css_path,
    reveal_css_path=None,
    print_margin: str = "2cm",
):
    """Generate @media print CSS safely with cssutils."""

    def load_css(path):
        if path is None:
            return None
        p = Path(path)
        if not p.exists():
            print(f"Warning: path not found, skipped: {p}")
            return None
        return p.read_text(encoding="utf-8")

    all_css = ""
    for path in [main_css_path, codeblock_css_path, reveal_css_path]:
        content = load_css(path)
        if content:
            all_css += content + "\n"

    if not all_css.strip():
        return "/* Error: no CSS content loaded */"

    sheet = cssutils.parseString(all_css)
    new_rules = []

    ui_keywords = {
        ".sidebar",
        ".app-nav",
        ".github-corner",
        ".progress",
        "#app",
        ".search",
        "section.cover",
        ".sidebar-toggle",
        ".emoji",
        "::-webkit-scrollbar",
        "main",
        ".anchor",
        ".md-sidebar-toc",
        ".cover-main",
        "body.close",
        "body.sticky",
    }

    disallowed_global_props = {
        "-webkit-overflow-scrolling",
        "-webkit-tap-highlight-color",
        "-webkit-text-size-adjust",
        "-webkit-touch-callout",
    }

    disallowed_print_props = {
        "font-family",
    }

    def is_ui_selector(selector_text: str) -> bool:
        return any(kw in selector_text for kw in ui_keywords)

    def convert_selector(selector_text: str) -> str:
        return (
            selector_text.replace(".markdown-preview.markdown-preview", "body").replace(
                ".markdown-preview", "body"
            )
        )

    def append_style_rule(rule_obj):
        selector = rule_obj.selectorText

        if not selector or is_ui_selector(selector):
            return

        new_rule = cssutils.css.CSSStyleRule()
        new_rule.selectorText = convert_selector(selector)

        for prop in rule_obj.style:
            if selector.strip() == "*" and prop.name in disallowed_global_props:
                continue
            if prop.name in disallowed_print_props:
                continue
            new_rule.style.setProperty(prop.name, prop.value, priority="important")

        if new_rule.style.length > 0:
            new_rules.append(new_rule.cssText)

    for rule in sheet:
        if rule.type == rule.STYLE_RULE:
            append_style_rule(rule)
        elif rule.type == rule.MEDIA_RULE:
            if "print" not in rule.media.mediaText.lower():
                continue

            nested_rules = []
            for nested in rule.cssRules:
                if nested.type != nested.STYLE_RULE:
                    continue

                selector = nested.selectorText
                if not selector or is_ui_selector(selector):
                    continue

                nested_rule = cssutils.css.CSSStyleRule()
                nested_rule.selectorText = convert_selector(selector)
                for prop in nested.style:
                    if prop.name in disallowed_print_props:
                        continue
                    nested_rule.style.setProperty(
                        prop.name,
                        prop.value,
                        priority="important",
                    )
                if nested_rule.style.length > 0:
                    nested_rules.append(nested_rule.cssText)

            if nested_rules:
                new_rules.extend(nested_rules)

    if not new_rules:
        return "/* No valid content style extracted */"

    output_lines = ["@media print {"]
    output_lines.append("  /* Auto-generated print style (cssutils based) */")
    output_lines.append("  body {")
    output_lines.append("    background: white !important;")
    output_lines.append("    color: black !important;")
    output_lines.append(f"    padding: {print_margin} !important;")
    output_lines.append("  }")
    output_lines.append("  table, th, td {")
    output_lines.append("    background: white !important;")
    output_lines.append("    color: black !important;")
    output_lines.append("  }")
    output_lines.append("  th {")
    output_lines.append("    font-weight: 700 !important;")
    output_lines.append("  }")
    output_lines.append("")
    output_lines.extend(new_rules)
    output_lines.append("  /* Fix Prism line-numbers layout in print mode */")
    output_lines.append("  .markdown-preview pre.line-numbers {")
    output_lines.append("    position: relative !important;")
    output_lines.append("    padding-left: 3.8em !important;")
    output_lines.append("    counter-reset: linenumber !important;")
    output_lines.append("  }")
    output_lines.append("  .markdown-preview pre.line-numbers > code {")
    output_lines.append("    white-space: pre !important;")
    output_lines.append("  }")
    output_lines.append("  .markdown-preview pre.line-numbers .line-numbers-rows {")
    output_lines.append("    position: absolute !important;")
    output_lines.append("    top: 1em !important;")
    output_lines.append("    left: 0 !important;")
    output_lines.append("    width: 3em !important;")
    output_lines.append("    font-size: inherit !important;")
    output_lines.append("    line-height: inherit !important;")
    output_lines.append("    letter-spacing: -1px !important;")
    output_lines.append("    border-right: 1px solid #d6d6d6 !important;")
    output_lines.append("    pointer-events: none !important;")
    output_lines.append("    user-select: none !important;")
    output_lines.append("  }")
    output_lines.append("  .markdown-preview pre.line-numbers .line-numbers-rows > span {")
    output_lines.append("    display: block !important;")
    output_lines.append("    line-height: inherit !important;")
    output_lines.append("    counter-increment: linenumber !important;")
    output_lines.append("  }")
    output_lines.append("  .markdown-preview pre.line-numbers .line-numbers-rows > span:before {")
    output_lines.append("    content: counter(linenumber) !important;")
    output_lines.append("    display: block !important;")
    output_lines.append("    line-height: inherit !important;")
    output_lines.append("    position: relative !important;")
    output_lines.append("    top: 0 !important;")
    output_lines.append("    text-align: right !important;")
    output_lines.append("    padding-right: 0.8em !important;")
    output_lines.append("    color: #808080 !important;")
    output_lines.append("  }")
    output_lines.append("  /* Keep MPE @import PDF (rendered as data SVG img) centered in print */")
    output_lines.append("  .markdown-preview img[src^=\"data:image/svg+xml\"] {")
    output_lines.append("    margin-left: auto !important;")
    output_lines.append("    margin-right: auto !important;")
    output_lines.append("  }")
    output_lines.append(
        "  .markdown-preview div[style*=\"text-align: center\"] img[src^=\"data:image/svg+xml\"] {"
    )
    output_lines.append("    display: inline-block !important;")
    output_lines.append("    margin-left: 0 !important;")
    output_lines.append("    margin-right: 0 !important;")
    output_lines.append("  }")
    output_lines.append(
        "  .markdown-preview div[style*=\"display: flex\"] > p:has(> img[src^=\"data:image/svg+xml\"]) {"
    )
    output_lines.append("    margin: 0 !important;")
    output_lines.append("  }")
    output_lines.append(
        "  .markdown-preview div[style*=\"display: flex\"] img[src^=\"data:image/svg+xml\"] {"
    )
    output_lines.append("    display: block !important;")
    output_lines.append("    margin: 0 !important;")
    output_lines.append("  }")
    output_lines.append("}")

    return "\n".join(output_lines)


FONT_FORMATS = {
    ".ttf": "truetype",
    ".otf": "opentype",
    ".woff": "woff",
    ".woff2": "woff2",
}


def _get_name_record(font: TTFont, name_ids: Tuple[int, ...]) -> Optional[str]:
    for name_id in name_ids:
        for record in font["name"].names:
            if record.nameID != name_id:
                continue
            try:
                value = record.toUnicode().strip()
            except Exception:
                continue
            if value:
                return value
    return None


def _normalize_font_family_name(name: str) -> str:
    return " ".join(name.split()).casefold()


def _safe_asset_stem(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    filtered = "".join(ch if ch.isalnum() else "-" for ch in ascii_text)
    cleaned = "-".join(part for part in filtered.split("-") if part)
    return cleaned.lower() or "font"


def _unique_keep_order(values: List[str]) -> List[str]:
    seen = set()
    ordered = []
    for item in values:
        key = item.strip()
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        ordered.append(key)
    return ordered


def _name_aliases(font: TTFont) -> List[str]:
    aliases: List[str] = []
    for record in font["name"].names:
        if record.nameID not in {1, 4, 6, 16, 17}:
            continue
        try:
            value = record.toUnicode().strip()
        except Exception:
            continue
        if value:
            aliases.append(value)
    return _unique_keep_order(aliases)


def _copy_font_to_assets(
    source_path: Path,
    assets_dir: Path,
    family_name: str,
    weight: int,
    style: str,
) -> str:
    assets_dir.mkdir(parents=True, exist_ok=True)
    stem = _safe_asset_stem(family_name)
    suffix = source_path.suffix.lower()
    dest_name = f"{stem}-{weight}-{style}{suffix}"
    dest_path = assets_dir / dest_name

    if not dest_path.exists() or source_path.stat().st_mtime > dest_path.stat().st_mtime:
        shutil.copy2(source_path, dest_path)

    return f"fonts/{dest_name}"


def read_font_metadata(font_path: Path) -> Tuple[str, int, str, str, List[str]]:
    if not font_path.exists():
        raise FileNotFoundError(f"Font file not found: {font_path}")
    if not font_path.is_file():
        raise ValueError(f"Font path is not a file: {font_path}")

    font_format = FONT_FORMATS.get(font_path.suffix.lower())
    if font_format is None:
        raise ValueError(
            f"Unsupported font file: {font_path} (.ttf/.otf/.woff/.woff2 only)"
        )

    with TTFont(font_path) as font:
        family_name = _get_name_record(font, (16, 1))
        if family_name is None:
            raise ValueError(f"Unable to determine font family name: {font_path}")
        aliases = _name_aliases(font)
        if family_name not in aliases:
            aliases.insert(0, family_name)

        weight = 400
        if "OS/2" in font:
            weight = int(getattr(font["OS/2"], "usWeightClass", 400) or 400)

        style = "normal"
        if "post" in font and float(getattr(font["post"], "italicAngle", 0) or 0) != 0:
            style = "italic"
        elif "head" in font and getattr(font["head"], "macStyle", 0) & 0b10:
            style = "italic"
        else:
            subfamily_name = _get_name_record(font, (17, 2)) or ""
            if "italic" in subfamily_name.casefold() or "oblique" in subfamily_name.casefold():
                style = "italic"

    return family_name, weight, style, font_format, aliases


def resolve_font_family(font_path: Path, font_assets_dir: Path) -> Tuple[str, str]:
    font_path = font_path.expanduser().resolve()
    base_family_name, _, _, _, _ = read_font_metadata(font_path)
    base_family_key = _normalize_font_family_name(base_family_name)

    variant_files: List[Tuple[Path, int, str, str, List[str]]] = []
    for candidate in sorted(font_path.parent.iterdir()):
        if candidate.suffix.lower() not in FONT_FORMATS or not candidate.is_file():
            continue

        try:
            family_name, weight, style, font_format, aliases = read_font_metadata(candidate)
        except Exception:
            continue

        if _normalize_font_family_name(family_name) != base_family_key:
            continue

        variant_files.append((candidate, weight, style, font_format, aliases))

    if not variant_files:
        raise ValueError(f"No usable font variants found for: {font_path}")

    variant_files.sort(key=lambda item: (item[1], item[2] == "italic", item[0].name.casefold()))

    css_lines = ["/* Auto-generated @font-face rules */"]
    for variant_path, weight, style, font_format, aliases in variant_files:
        asset_rel_path = _copy_font_to_assets(
            source_path=variant_path,
            assets_dir=font_assets_dir,
            family_name=base_family_name,
            weight=weight,
            style=style,
        )
        local_sources = ", ".join(f"local('{name}')" for name in _unique_keep_order(aliases))
        if local_sources:
            src_value = f"{local_sources}, url('{asset_rel_path}') format('{font_format}')"
        else:
            src_value = f"url('{asset_rel_path}') format('{font_format}')"
        css_lines.append("@font-face {")
        css_lines.append(f"  font-family: '{base_family_name}';")
        css_lines.append(f"  src: {src_value};")
        css_lines.append(f"  font-weight: {weight};")
        css_lines.append(f"  font-style: {style};")
        css_lines.append("  font-display: swap;")
        css_lines.append("}")
        css_lines.append("")

    return base_family_name, "\n".join(css_lines).strip()


def build_style_blocks(
    extension_dir: Path,
    font_path: Optional[Path],
    main_css_path: Path,
    codeblock_css_path: Path,
    print_margin: str,
    font_assets_dir: Path,
    code_font_path: Optional[Path] = None,
    enable_parser: bool = False,
) -> List[str]:
    blocks: List[str] = []

    font_family_name = None
    content_font_faces = None
    if font_path is not None:
        font_family_name, content_font_faces = resolve_font_family(font_path, font_assets_dir)
        blocks.append(content_font_faces)

    code_font_family = None
    if code_font_path is not None:
        code_font_family, code_font_faces = resolve_font_family(code_font_path, font_assets_dir)
        if code_font_faces != content_font_faces:
            blocks.append(code_font_faces)

        blocks.append(
                """
.markdown-preview.markdown-preview {
"""
        )

        if font_family_name:
                blocks.append(
                        f"""
  *:not(:is(
    pre, pre *, code, code *, kbd, kbd *, samp, samp *,
    .katex, .katex *, .MathJax, .MathJax *, mjx-container, mjx-container *
  )) {{
    font-family: '{font_family_name}', 'Source Sans Pro', 'Noto Sans CJK SC', 'Noto Sans SC', sans-serif !important;
  }}
"""
                )

    blocks.append(
        """
  * {
    page-break-inside: avoid !important;
    page-break-before: avoid !important;
    page-break-after: avoid !important;
  }
"""
    )

    if not enable_parser:
        for i in range(1, 101):
            blocks.append(
                f"""
  img[alt*="{i}"] {{
    width: {i}% !important;
    height: auto;
    display: block;
    margin: 0 auto;
  }}
"""
            )

    blocks.append(
        """
  img[alt$="r"]:not([alt*="L"]):not([alt*="R"]):not([alt*="f"]) {
    display: inline-block !important;
    vertical-align: middle;
  }
"""
    )
    blocks.append(
        """
  :has(> img[alt$="r"]:not([alt*="L"]):not([alt*="R"]):not([alt*="f"])) {
    text-align: center;
  }
"""
    )
    blocks.append(
        """
  img[alt*="L"]:not([alt*="f"]) {
    display: block !important;
    margin-left: 0 !important;
    margin-right: auto !important;
  }
"""
    )
    blocks.append(
        """
  img[alt*="R"]:not([alt*="f"]) {
    display: block !important;
    margin-left: auto !important;
    margin-right: 0 !important;
  }
"""
    )
    blocks.append(
        """
  img[alt*="Lf"] {
    float: left;
  }
"""
    )
    blocks.append(
        """
  img[alt*="Rf"] {
    float: right;
  }
"""
    )
    blocks.append(
                """
    figure[alt*="Lf"] {
        float: left;
        margin: 0 1em 1em 0;
    }

    figure[alt*="Rf"] {
        float: right;
        margin: 0 0 1em 1em;
    }

    figure[alt*="Lf"] > img,
    figure[alt*="Rf"] > img {
        float: none !important;
        display: block !important;
        margin: 0 !important;
    }
"""
        )

    blocks.append(
        """
  /* Keep headings and separators from wrapping beside floated images. */
  h1, h2, h3, h4, h5, h6, hr {
    clear: both;
  }
"""
    )

    if code_font_family:
        blocks.append(
            f"""
    pre, pre *, code, code *, kbd, kbd *, samp, samp *, pre[class*="language-"], pre[class*="language-"] *, code[class*="language-"], code[class*="language-"] * {{
        font-family: '{code_font_family}', monospace !important;
  }}

    .line-numbers-rows, .line-numbers-rows > span:before {{
        font-family: '{code_font_family}', monospace !important;
    }}
"""
        )

    blocks.append(
        """
}
"""
    )

    blocks.append(
        generate_print_style(
            main_css_path,
            codeblock_css_path,
            print_margin=print_margin,
        )
    )

    return blocks


def build_parser_blocks(mappers: str) -> Tuple[List[str], List[str]]:
    parser_blocks: List[str] = []
    html_blocks: List[str] = []
    # PDF center
    parser_blocks.append(
r"""
    const regex = /^@import\s+"(.*\.pdf)"\s*(\{.*?\})?/mg;
    markdown = markdown.replace(regex, (match, pdf, argument) => {
      return `
<div style="display: flex; justify-content: center; flex-wrap: wrap;">

@import "${pdf}"{${argument}}

</div>`
    });
"""
    )
    # Image alt size
    html_blocks.append(
"""
        function extractWidthFromAlt(alt) {
            if (!alt) return null;

            // 支持: 25, 25%, 300px, 25r, 30R, 40Lf, 40Rf
            const token = alt.trim().match(/^(\\d{1,4})(?:\\s*(px|%))?/i);
            if (!token) return null;

            const value = Number(token[1]);
            if (!Number.isFinite(value) || value <= 0) return null;

            const unit = (token[2] || '%').toLowerCase();
            if (unit === 'px') {
                return `${value}px`;
            }
            return `${Math.min(value, 100)}%`;
        }

        function resolveLayoutMode(alt) {
            const text = (alt || '').trim();
            if (text.includes('Lf') || text.includes('Rf')) {
                return 'float';
            }
            if (text.includes('L')) {
                return 'left';
            }
            if (text.includes('R')) {
                return 'right';
            }
            if (text.endsWith('r')) {
                return 'inline';
            }
            return 'center';
        }

        function mergeStyle(existingStyle, widthValue, alt) {
            const styleMap = new Map();
            const styleText = existingStyle || '';

            styleText
                .split(';')
                .map((s) => s.trim())
                .filter(Boolean)
                .forEach((entry) => {
                    const idx = entry.indexOf(':');
                    if (idx <= 0) return;
                    const key = entry.slice(0, idx).trim().toLowerCase();
                    const value = entry.slice(idx + 1).trim();
                    if (!key || !value) return;
                    styleMap.set(key, value);
                });

            styleMap.set('width', `${widthValue} !important`);
            styleMap.set('height', 'auto !important');

            const layoutMode = resolveLayoutMode(alt);

            // Clear conflicting keys before applying our layout intent.
            styleMap.delete('margin');
            styleMap.delete('margin-left');
            styleMap.delete('margin-right');
            styleMap.delete('vertical-align');

            if (layoutMode === 'inline') {
                styleMap.set('display', 'inline-block !important');
                styleMap.set('margin', '0 !important');
                styleMap.set('vertical-align', 'middle !important');
            } else if (layoutMode === 'left') {
                styleMap.set('display', 'block !important');
                styleMap.set('margin-left', '0 !important');
                styleMap.set('margin-right', 'auto !important');
            } else if (layoutMode === 'right') {
                styleMap.set('display', 'block !important');
                styleMap.set('margin-left', 'auto !important');
                styleMap.set('margin-right', '0 !important');
            } else if (layoutMode === 'center') {
                styleMap.set('display', 'block !important');
                styleMap.set('margin', '0 auto !important');
            } else {
                // float mode: keep width/height only; let CSS alt rules control float/layout.
                styleMap.delete('display');
            }

            return Array.from(styleMap.entries())
                .map(([k, v]) => `${k}: ${v}`)
                .join('; ');
        }

        html = html.replace(/<img\\b[^>]*>/gi, (imgTag) => {
            const altMatch = imgTag.match(/\\balt=(['\"])(.*?)\\1/i);
            const alt = altMatch ? altMatch[2] : '';
            const widthValue = extractWidthFromAlt(alt);
            if (!widthValue) return imgTag;

            const styleMatch = imgTag.match(/\\bstyle=(['\"])(.*?)\\1/i);
            const mergedStyle = mergeStyle(styleMatch ? styleMatch[2] : '', widthValue, alt);

            if (styleMatch) {
                return imgTag.replace(styleMatch[0], `style=\"${mergedStyle}\"`);
            }
            return imgTag.replace(/\\/>$/, ` style=\"${mergedStyle}\"/>`).replace(/>$/, ` style=\"${mergedStyle}\">`);
        });
"""
    )
    # Table
    html_blocks.append(
        r"""
        const cr_regex = /(<td.*?)>(:?c\d+:?|:?r\d+:?|:?c\d+r\d+:?|:?r\d+c\d+:?)\s+(.*)<\/td>/g;
        html = html.replace(cr_regex, (match, tdStart, spanInfo, content) => {
            let colspan = 1;
            let rowspan = 1;
            let align = '';
            const colMatch = spanInfo.match(/c(\d+)/);
            if (colMatch) {
                colspan = parseInt(colMatch[1], 10);
            }
            const rowMatch = spanInfo.match(/r(\d+)/);
            if (rowMatch) {
                rowspan = parseInt(rowMatch[1], 10);
            }
            if (spanInfo.startsWith(':') && spanInfo.endsWith(':')) {
                align = 'center';
            } else if (spanInfo.startsWith(':')) {
                align = 'left';
            } else if (spanInfo.endsWith(':')) {
                align = 'right';
            }
            if (align) {
                const styleMatch = tdStart.match(/style="(.*?)"/i);
                if (styleMatch) {
                    tdStart = tdStart.replace(styleMatch[0], `style=\"${styleMatch[2]} text-align: ${align} !important;\"`);
                } else {
                    tdStart += ` style=\"text-align: ${align} !important;\"`;
                }
            }
            return `${tdStart} colspan="${colspan}" rowspan="${rowspan}">${content}</td>`;
        });
        const rm_regex = /<td[^>]*>\\<\/td>/g;
        html = html.replace(rm_regex, '');
        const esc_regex = /<td([^>]*)>\\\\<\/td>/g;
        html = html.replace(esc_regex, '<td$1>\\</td>');
        const th_regex = /(<th.*?)>(:?c\d+:?)\s+(.*)<\/th>/g;
        html = html.replace(th_regex, (match, thStart, spanInfo, content) => {
            let colspan = 1;
            let align = '';
            const colMatch = spanInfo.match(/c(\d+)/);
            if (colMatch) {
                colspan = parseInt(colMatch[1], 10);
            }
            if (spanInfo.startsWith(':') && spanInfo.endsWith(':')) {
                align = 'center';
            } else if (spanInfo.startsWith(':')) {
                align = 'left';
            } else if (spanInfo.endsWith(':')) {
                align = 'right';
            }
            if (align) {
                const styleMatch = thStart.match(/style="(.*?)"/i);
                if (styleMatch) {
                    thStart = thStart.replace(styleMatch[0], `style=\"${styleMatch[2]} text-align: ${align} !important;\"`);
                } else {
                    thStart += ` style=\"text-align: ${align} !important;\"`;
                }
            }
            return `${thStart} colspan="${colspan}">${content}</th>`;
        });
        const rm_th_regex = /<th[^>]*>\\<\/th>/g;
        html = html.replace(rm_th_regex, '');
        const esc_th_regex = /<th([^>]*)>\\\\<\/th>/g;
        html = html.replace(esc_th_regex, '<th$1>\\</th>');
        """
    )
    # Image title
    
    html_blocks.append(
        r"""
        html = html.replace(
            /<img[^\>]*>/g,
            (imgTag) => {
                let match = imgTag.match(/alt=(['"])(.*?)\1/i);
                const alt = match ? match[2] : '';
                match = alt.match(/\((.+)\)/i);
                let caption = match ? match[1] : '';
                let format = alt.replace(`(${caption})`, '').trim();
                if (!caption) return imgTag;
                const isFloat = format.includes('Lf') || format.includes('Rf');
                const isSideAligned = !isFloat && (format.includes('L') || format.includes('R'));
                if (!format.includes("r")) {
                    const finalCaption = caption.startsWith('.') ? `图@COUNT_PLACEHOLDER@:\t` + caption.slice(1) : caption;
                    if (isFloat) {
                        match = imgTag.match(/style=(['"])(.*?)\1/i);
                        let style = match ? match[2] : '';
                        style = style.replace(/float:\s*(left|right)\s*!?important?/gi, '');
                        style = style.replace(/display:\s*inline-block/g, 'display: block');
                        match = style.match(/width:\s*(\d{1,4}(?:px|%))/i);
                        const width = match ? match[1] : '100%';
                        style = style.replace(/width:\s*\d{1,4}(?:px|%)/g, `width: 100%`);
                        if (!/display\s*:/i.test(style)) {
                            style = `${style}; display: block`;
                        }
                        style = style
                            .split(';')
                            .map((s) => s.trim())
                            .filter(Boolean)
                            .join('; ');
                        if (imgTag.match(/style=(['"])(.*?)\1/i)) {
                            imgTag = imgTag.replace(/style=(['"])(.*?)\1/i, `style="${style}"`);
                        } else {
                            imgTag = imgTag.replace(/\/>$/, ` style="${style}"/>`).replace(/>$/, ` style="${style}">`);
                        }
                        const floatDir = format.includes('Rf') ? 'right' : 'left';
                        const margin = floatDir === 'left' ? '0 1em 1em 0' : '0 0 1em 1em';
                        return `<figure style="float: ${floatDir}; width: ${width}; margin: ${margin};" alt="${format}">
${imgTag}
<figcaption style="text-align: center;">${finalCaption}</figcaption>
</figure>`;
                    }

                    if (isSideAligned) {
                        match = imgTag.match(/style=(['"])(.*?)\1/i);
                        let style = match ? match[2] : '';
                        style = style.replace(/display:\s*inline-block/g, 'display: block');
                        match = style.match(/width:\s*(\d{1,4}(?:px|%))/i);
                        const width = match ? match[1] : '100%';
                        style = style.replace(/width:\s*\d{1,4}(?:px|%)/g, `width: 100%`);
                        style = style
                            .split(';')
                            .map((s) => s.trim())
                            .filter(Boolean)
                            .join('; ');
                        if (imgTag.match(/style=(['"])(.*?)\1/i)) {
                            imgTag = imgTag.replace(/style=(['"])(.*?)\1/i, `style="${style}"`);
                        } else {
                            imgTag = imgTag.replace(/\/>$/, ` style="${style}"/>`).replace(/>$/, ` style="${style}">`);
                        }

                        const margin = format.includes('R') ? '0 0 1em auto' : '0 auto 1em 0';
                        return `<figure style="width: ${width}; margin: ${margin};" alt="${format}">
${imgTag}
<figcaption style="text-align: center;">${finalCaption}</figcaption>
</figure>`;
                    }

                    return `<figure>
${imgTag}
<figcaption style="text-align: center;">${finalCaption}</figcaption>
</figure>`;
                }
                match = imgTag.match(/style=(['"])(.*?)\1/i);
                let style = match ? match[2] : '';
                style = style.replace(/display:\s*inline-block/g, 'display: block');
                match = style.match(/width:\s*(\d{1,4}(?:px|%))/i);
                const width = match ? match[1] : '100%';
                style = style.replace(/width:\s*\d{1,4}(?:px|%)/g, `width: 100%`);
                imgTag = imgTag.replace(/style=(['"])(.*?)\1/i, `style="${style}"`);
                const finalCaption = caption.startsWith('.') ? `图@COUNT_PLACEHOLDER@:\t` + caption.slice(1) : caption;
                return `<figure style="width: ${width}; margin: 0 auto; display: inline-block;" alt="${format}">
${imgTag}
<figcaption style="text-align: center;">${finalCaption}</figcaption>
</figure>`;
            }
        )
    
        html = html.replace(
            /((<figure.*?alt=["'].*?r.*?["'].*?>.*?<\/figure>\s*)+)/gs,
            (match) => {
                let firstFigure = match.split('</figure>')[0];
                let captionMatch = firstFigure.match(/<figcaption.*?>(.*?)<\/figcaption>/i);
                let caption = captionMatch ? captionMatch[1] : '';
                let generalCaptionMatch = caption.match(/\((.+)\)/i);
                let generalCaption = generalCaptionMatch ? generalCaptionMatch[1] : '';
                if (generalCaption) {
                    let modifiedCaption = caption.replace( /\((.+)\)/i, "");
                    let modifiedCaptionTag = captionMatch[0].replace(caption, modifiedCaption);
                    let modifiedFirstFigure = firstFigure.replace(captionMatch[0], modifiedCaptionTag);
                    match = match.replace(firstFigure, modifiedFirstFigure);
                    generalCaption = generalCaption.startsWith('.') ? `图@COUNT_PLACEHOLDER@:\t` + generalCaption.slice(1) : generalCaption;
                    generalCaption = `<figcaption style="text-align: center;">${generalCaption}</figcaption>`;
                }
                return `<figure style="text-align: center;">
${match}
${generalCaption || ''}
</figure>`;
            }
        )

        let cnt = 0;
        html = html.replace(/@COUNT_PLACEHOLDER@/g, (match) => {
            cnt += 1;
            return cnt;
        });
"""
    )
    # title prefix
    levels = []
    for i in re.split(r"\s*,\s*", mappers.strip()):
        if i not in {"roman", "romanUpper", "latin", "latinUpper", "chinese", "number", "none"}:
            raise ValueError(f"Unsupported mapper: {i}, only <roman|romanUpper|latin|latinUpper|chinese|number|none> are supported.")
        levels.append(i)
    while len(levels) < 6:
        levels.append("none")
    if len(levels) > 6:
        raise ValueError(f"Too many mappers: {len(levels)}, at most 6 levels are supported.")
    parser_blocks.append(r"""
function roman(num, prefix) {
    if (typeof num !== 'number' || num < 1 || num > 3999) {
        return '';
    }
    const values = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1];
    const symbols = ['m', 'cm', 'd', 'cd', 'c', 'xc', 'l', 'xl', 'x', 'ix', 'v', 'iv', 'i'];
    let result = '';
    for (let i = 0; i < values.length; i++) {
        while (num >= values[i]) {
            result += symbols[i];
            num -= values[i];
        }
    }
    return result + ") ";
}
function romanUpper(num, prefix) {
    return roman(num, prefix).toUpperCase();
}
function latin(num, prefix) {
    if (typeof num !== 'number' || num <= 0 || !Number.isInteger(num)) {
        return '';
    }
    let result = '';
    let n = num;
    while (n > 0) {
        n--;
        const remainder = n % 26;
        result = String.fromCharCode(97 + remainder) + result;
        n = Math.floor(n / 26);
    }
    return result + ") ";
}
function latinUpper(num, prefix) {
    return latin(num, prefix).toUpperCase();
}
function chinese(num, prefix) {
    if (typeof num !== 'number' || num <= 0 || !Number.isInteger(num)) {
        return '';
    }
    const digits = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九'];
    const units = ['', '十', '百', '千'];
    const sectionUnits = ['', '万', '亿', '兆'];
    let numStr = num.toString();
    const sections = [];
    while (numStr.length > 4) {
        sections.push(numStr.slice(-4));
        numStr = numStr.slice(0, -4);
    }
    if (numStr.length > 0) sections.push(numStr);
    sections.reverse();
    function convertSection(sectionStr) {
        while (sectionStr.length < 4) sectionStr = '0' + sectionStr;
        let result = '';
        let hasOutput = false;
        let needZero = false;
        for (let i = 0; i < 4; i++) {
            const digit = parseInt(sectionStr[i], 10);
            if (digit !== 0) {
                if (needZero) {
                    result += '零';
                    needZero = false;
                }
                result += digits[digit] + units[3 - i];
                hasOutput = true;
            } else {
                if (hasOutput) {
                    needZero = true;
                }
            }
        }
        return result;
    }
    let chinese = '';
    let lastNonZeroExists = false;
    let needZeroFromPrevZero = false;
    for (let i = 0; i < sections.length; i++) {
        const sectionVal = parseInt(sections[i], 10);
        const sectionChinese = sectionVal === 0 ? '' : convertSection(sections[i]);
        const sectionUnit = sectionUnits[sections.length - 1 - i];
        if (sectionVal === 0) {
            needZeroFromPrevZero = true;
        } else {
            let needPrependZero = false;
            if (needZeroFromPrevZero) {
                needPrependZero = true;
                needZeroFromPrevZero = false;
            } else if (lastNonZeroExists && sectionVal < 1000) {
                needPrependZero = true;
            }
            if (needPrependZero) {
                chinese += '零';
            }
            chinese += sectionChinese + sectionUnit;
            lastNonZeroExists = true;
        }
    }
    if (chinese.startsWith('一十')) {
        chinese = chinese.slice(1);
    }
    return (chinese || '零') + "、";
}
function number(num, prefix) {
    if (typeof num !== 'number' || num <= 0 || !Number.isInteger(num)) {
        return '';
    }
    if (/^\d/.test(prefix)) {
        return `${prefix.replace(/\.?\s?$/i, "")}.\u200B${num} `;
    }
    return `${num}\u200B. `;
}
function none(num, prefix) {
    return '';
}
function preprocessMarkdown(markdown, mappers) {
    let prefix = [null, null, null, null, null, null];
    let counters = [0, 0, 0, 0, 0, 0];
    markdown = markdown.replace(
        /^(#{1,6})\s*?\.(.*?)$/gm,
        (match, hashes, title) => {
            const level = hashes.length - 1;
            counters[level]++;
            for (let i = level + 1; i < 6; i++) {
                counters[i] = 0;
                prefix[i] = null;
            }
            let lastPrefix = "";
            let i = level - 1;
            while (i >= 0) {
                if (prefix[i] === null) {
                    i--;
                    continue;
                }
                lastPrefix = prefix[i];
                break;
            }
            const newPrefix = mappers[level](
                counters[level],
                lastPrefix
            )
            prefix[level] = newPrefix;
            return `${hashes} ${newPrefix}${title}`;
        }
    )
    return markdown;
}
mappers = [@MAPPER_PLACEHOLDER@];
markdown = preprocessMarkdown(markdown, mappers);
""".replace("@MAPPER_PLACEHOLDER@", ", ".join(levels))
    )
    return parser_blocks, html_blocks


def write_output(
    output_path: Path,
    blocks: List[str],
    parse_blocks: List[str] = [],
    html_blocks: List[str] = [],
) -> None:
    try:
        import jsbeautifier
    except ImportError:
        jsbeautifier = None
    try:
        import cssbeautifier
    except ImportError:
        cssbeautifier = None
    output_path.mkdir(parents=True, exist_ok=True)
    style_less = output_path / "style.less"
    text = "\n".join(map(lambda x: x.strip("\n"), blocks))
    if cssbeautifier:
        text = cssbeautifier.beautify(text, {"indent_size": 2})
    style_less.write_text(text, encoding="utf-8")
    print(f"Generated style.less written to: {style_less.resolve()}")
    parser_blocks: List[str] = []
    if parse_blocks:
        parser_blocks.append(
            "  onWillParseMarkdown: async function(markdown) {"
        )
        parser_blocks.extend(parse_blocks)
        parser_blocks.append("    return markdown;")
        parser_blocks.append("  },")
    elif html_blocks:
        parser_blocks.append(
            "  onWillParseMarkdown: async function(markdown) { return markdown; },"
        )
    if html_blocks:
        parser_blocks.append(
            "  onDidParseMarkdown: async function(html) {"
        )
        parser_blocks.extend(html_blocks)
        parser_blocks.append("    return html;")
        parser_blocks.append("  },")
    elif parse_blocks:
        parser_blocks.append("  onDidParseMarkdown: async function(html) { return html; },")
    if parser_blocks:
        parser_js = output_path / "parser.js"
        output = "\n" + "\n".join(map(lambda x: x.strip("\n"), parser_blocks)) + "\n"
        output = f"({{{output}}})"
        if jsbeautifier:
            output = jsbeautifier.beautify(output, {"indent_size": 2})
        parser_js.write_text(output, encoding="utf-8")
        print(f"Generated parser.js written to: {parser_js.resolve()}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate Crossnote style.less with more features."
    )
    parser.add_argument(
        "--extensions-root",
        type=Path,
        default=DEFAULT_EXTENSIONS_ROOT,
        help="Base directory containing VS Code extensions.",
    )
    parser.add_argument(
        "--extension-pattern",
        type=str,
        default="shd101wyy.markdown-preview-enhanced-*",
        help="Glob pattern for the markdown-preview-enhanced extension directory.",
    )
    parser.add_argument(
        "--extension-dir",
        type=Path,
        default=None,
        help="Explicit extension directory (overrides pattern matching).",
    )
    parser.add_argument(
        "--font",
        type=Path,
        default=None,
        help=(
            "Optional font file path for the main document font. The script reads its family "
            "name from metadata and scans sibling files in the same directory for variants. "
            "If omitted, document body font-family will not be overridden."
        ),
    )
    parser.add_argument(
        "--main-css",
        type=Path,
        required=True,
        help=(
            "Main theme CSS path. If relative, it is resolved under "
            "<extension-dir>/crossnote/styles/."
        ),
    )
    parser.add_argument(
        "--codeblock-css",
        type=Path,
        required=True,
        help=(
            "Code block theme CSS path. If relative, it is resolved under "
            "<extension-dir>/crossnote/styles/."
        ),
    )
    parser.add_argument(
        "--code-font",
        type=Path,
        default=None,
        help=(
            "Optional font file path for code blocks. The script reads its family name "
            "from metadata and scans sibling files in the same directory for variants."
        ),
    )
    parser.add_argument(
        "--print-margin",
        type=str,
        default="5mm",
        help=(
            "Print content margin value used as CSS padding in @media print body. "
            "Supports CSS length units and 1-4 value syntax, e.g. '2cm', '20mm', '1in 0.8in'."
        ),
    )
    parser.add_argument(
        "--enable-parser",
        action="store_true",
        help="Generate features that require parser.js support."
    )
    parser.add_argument(
        "--auto-count",
        type=str,
        default="none, chinese, number, number, latin, roman",
        help=(
            "Comma-separated list of title auto-count formatter for heading levels 1-6. "
            "Supported formatter: roman, romanUpper, latin, latinUpper, chinese, number, none."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output crossnote style directory (style.less and optionally parser.js will be written here).",
    )
    return parser


def resolve_crossnote_style_path(extension_dir: Path, css_path: Path) -> Path:
    if css_path.is_absolute():
        return css_path
    return extension_dir / "crossnote" / "styles" / css_path


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    extension_dir = resolve_extension_dir(
        extensions_root=args.extensions_root,
        extension_pattern=args.extension_pattern,
        explicit_extension_dir=args.extension_dir,
    )

    main_css_path = resolve_crossnote_style_path(
        extension_dir=extension_dir,
        css_path=args.main_css,
    )
    codeblock_css_path = resolve_crossnote_style_path(
        extension_dir=extension_dir,
        css_path=args.codeblock_css,
    )

    print_margin = args.print_margin.strip()
    output_path = args.output.expanduser().resolve()
    font_assets_dir = output_path / "fonts"

    blocks = build_style_blocks(
        extension_dir=extension_dir,
        font_path=args.font,
        main_css_path=main_css_path,
        codeblock_css_path=codeblock_css_path,
        print_margin=print_margin,
        font_assets_dir=font_assets_dir,
        code_font_path=args.code_font,
        enable_parser=args.enable_parser,
    )
    
    if args.enable_parser:
        parse_blocks, html_blocks = build_parser_blocks(args.auto_count)
    else:
        parse_blocks, html_blocks = [], []

    write_output(output_path, blocks, parse_blocks, html_blocks)


if __name__ == "__main__":
    main()
