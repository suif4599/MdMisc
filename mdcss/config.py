import argparse
import json
from pathlib import Path
from typing import Any

HOME = Path.home()
SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_EXTENSIONS_ROOT = HOME / ".vscode" / "extensions"
DEFAULT_OUTPUT = HOME / ".local" / "state" / "crossnote"
CONFIG_FILE_NAME = "config.json"


def load_config() -> dict[str, Any]:
    """Load user configuration from config.json next to mdcss.py.

    Returns a dict; missing file or parse errors result in an empty dict + warning.
    """
    config_path = SCRIPT_DIR / CONFIG_FILE_NAME
    if not config_path.exists():
        return {}

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Warning: failed to parse {config_path}: {exc}")
        return {}

    if not isinstance(data, dict):
        print(f"Warning: {config_path} must contain a JSON object, got {type(data).__name__}")
        return {}

    return data


def _resolve_path(value: str | None) -> Path | None:
    """Convert a config string value to a Path, expanding ~ only.

    Relative paths are left relative — resolved against cwd at use-site.
    Returns None for empty or None values.
    """
    if not value:
        return None
    return Path(value).expanduser()


def _raw_path(value: str | None) -> Path | None:
    """Like _resolve_path but keeps relative paths untouched.

    Use for main_css / codeblock_css so they stay as extension-relative
    strings for resolve_crossnote_style_path() to handle later.
    Returns None for empty or None values.
    """
    if not value:
        return None
    return Path(value).expanduser()


def _serialize_path(value: Path | None) -> str | None:
    """Inverse of _resolve_path: make a Path portable for config.json.

    Priority: relative-to-cwd → ~/... → absolute.
    """
    if value is None:
        return None
    p = Path(value).expanduser().resolve()
    try:
        return str(p.relative_to(Path.cwd()))
    except ValueError:
        pass
    try:
        return str(Path("~") / p.relative_to(HOME))
    except (ValueError, OSError):
        pass
    return str(p)


def save_config(args: argparse.Namespace) -> None:
    """Write effective settings to mdcss/config.json."""
    config_path = SCRIPT_DIR / CONFIG_FILE_NAME
    data: dict[str, Any] = {}

    # Path-valued keys
    for key in [
        "extensions_root", "extension_dir", "font", "code_font", "output",
    ]:
        value = _serialize_path(getattr(args, key, None))
        if value is not None:
            data[key] = value

    # main_css / codeblock_css — keep extension-relative path as-is
    for key in ["main_css", "codeblock_css"]:
        val: Path | None = getattr(args, key, None)
        if val is not None:
            data[key] = str(val) if not val.is_absolute() else _serialize_path(val)

    # String-valued keys
    for key in ["extension_pattern", "print_margin", "auto_count"]:
        val = getattr(args, key, None)
        if val is not None:
            data[key] = val

    # Boolean flags
    for key in [
        "expand_detail", "enable_parser", "enable_header",
        "enable_table_horizontal_scroll",
    ]:
        val = getattr(args, key, None)
        if val:
            data[key] = True

    config_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Config saved to: {config_path}")


def resolve_extension_dir(
    extensions_root: Path,
    extension_pattern: str,
    explicit_extension_dir: Path | None = None,
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


def resolve_crossnote_style_path(extension_dir: Path, css_path: Path) -> Path:
    if css_path.is_absolute():
        return css_path
    return extension_dir / "crossnote" / "styles" / css_path


def build_parser(config: dict[str, Any]) -> argparse.ArgumentParser:
    cfg: dict[str, Any] = config  # shorthand

    parser = argparse.ArgumentParser(
        description="Generate Crossnote style.less with more features."
    )
    parser.add_argument(
        "--extensions-root",
        type=Path,
        default=_resolve_path(cfg.get("extensions_root")) or DEFAULT_EXTENSIONS_ROOT,
        help="Base directory containing VS Code extensions.",
    )
    parser.add_argument(
        "--extension-pattern",
        type=str,
        default=cfg.get("extension_pattern", "shd101wyy.markdown-preview-enhanced-*"),
        help="Glob pattern for the markdown-preview-enhanced extension directory.",
    )
    parser.add_argument(
        "--extension-dir",
        type=Path,
        default=_resolve_path(cfg.get("extension_dir")),
        help="Explicit extension directory (overrides pattern matching).",
    )
    parser.add_argument(
        "--expand-detail",
        action="store_true",
        default=cfg.get("expand_detail", False),
        help="Expand details in print mode automatically.",
    )
    parser.add_argument(
        "--font",
        type=Path,
        default=_resolve_path(cfg.get("font")),
        help=(
            "Optional font file path for the main document font. The script reads its family "
            "name from metadata and scans sibling files in the same directory for variants. "
            "If omitted, document body font-family will not be overridden."
        ),
    )
    parser.add_argument(
        "--main-css",
        type=Path,
        default=_raw_path(cfg.get("main_css")),
        help=(
            "Main theme CSS path. If relative, it is resolved under "
            "<extension-dir>/crossnote/styles/."
        ),
    )
    parser.add_argument(
        "--codeblock-css",
        type=Path,
        default=_raw_path(cfg.get("codeblock_css")),
        help=(
            "Code block theme CSS path. If relative, it is resolved under "
            "<extension-dir>/crossnote/styles/."
        ),
    )
    parser.add_argument(
        "--code-font",
        type=Path,
        default=_resolve_path(cfg.get("code_font")),
        help=(
            "Optional font file path for code blocks. The script reads its family name "
            "from metadata and scans sibling files in the same directory for variants."
        ),
    )
    parser.add_argument(
        "--print-margin",
        type=str,
        default=cfg.get("print_margin", "5mm"),
        help=(
            "Print content margin value used as CSS padding in @media print body. "
            "Supports CSS length units and 1-4 value syntax, e.g. '2cm', '20mm', '1in 0.8in'."
        ),
    )
    parser.add_argument(
        "--enable-parser",
        action="store_true",
        default=cfg.get("enable_parser", False),
        help="Generate features that require parser.js support.",
    )
    parser.add_argument(
        "--enable-header",
        action="store_true",
        default=cfg.get("enable_header", False),
        help="Generate features that require head.html support.",
    )
    parser.add_argument(
        "--enable-table-horizontal-scroll",
        action="store_true",
        default=cfg.get("enable_table_horizontal_scroll", False),
        help=(
            "Allow horizontal scrolling for wide tables (keep current behavior). "
            "If not set, tables will avoid horizontal scroll and force content wrapping."
        ),
    )
    parser.add_argument(
        "--auto-count",
        type=str,
        default=cfg.get("auto_count", "none, chinese, number, number, latin, roman"),
        help=(
            "Comma-separated list of title auto-count formatter for heading levels 1-6. "
            "Supported formatter: roman, romanUpper, latin, latinUpper, chinese, number, none."
        )
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_resolve_path(cfg.get("output")) or DEFAULT_OUTPUT,
        help="Output crossnote style directory (style.less and optionally parser.js will be written here).",
    )
    parser.add_argument(
        "--save-config",
        action="store_true",
        help="Save the effective settings (after CLI and config merge) to config.json and exit.",
    )
    return parser
