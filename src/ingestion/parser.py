"""Main document parser - delegates to format-specific parsers."""

from pathlib import Path

from ..models import ParsedDocument, SourceType
from .markdown import parse_markdown
from .pdf import parse_pdf
from .url import parse_url


def detect_source_type(source: str | Path) -> SourceType:
    """Detect the type of source document."""
    if isinstance(source, Path):
        source = str(source)

    # If the string is too long, it's definitely content, not a path
    if len(source) > 500:
        return SourceType.MARKDOWN

    # Check if it's a URL first (before trying path operations)
    if source.startswith(("http://", "https://")):
        return SourceType.URL

    # Check if it's a file path
    path = Path(source)
    try:
        if path.exists():
            suffix = path.suffix.lower()
            if suffix in (".md", ".markdown"):
                return SourceType.MARKDOWN
            elif suffix == ".pdf":
                return SourceType.PDF
            elif suffix in (".txt", ".text"):
                return SourceType.TEXT
            else:
                # Try to read and detect
                return SourceType.TEXT
    except OSError:
        # Path operation failed (e.g., filename too long)
        pass

    # Otherwise treat as raw text/markdown
    return SourceType.MARKDOWN


def parse_document(source: str | Path) -> ParsedDocument:
    """Parse a document from various formats.

    Args:
        source: File path, URL, or raw content

    Returns:
        ParsedDocument with extracted content

    Raises:
        NotImplementedError: If the source type is not yet supported
    """
    source_type = detect_source_type(source)

    if source_type == SourceType.MARKDOWN:
        return parse_markdown(source)
    elif source_type == SourceType.PDF:
        return parse_pdf(source)
    elif source_type == SourceType.URL:
        return parse_url(source)
    elif source_type == SourceType.TEXT:
        # Treat as markdown
        return parse_markdown(source)
    else:
        raise ValueError(f"Unknown source type: {source_type}")


def extract_sections_by_range(
    document: ParsedDocument,
    start_heading: str | None = None,
    end_heading: str | None = None,
) -> list:
    """Extract a range of sections from a document.

    Args:
        document: The parsed document
        start_heading: Heading to start from (inclusive). If None, starts from beginning.
        end_heading: Heading to end at (inclusive). If None, goes to end.

    Returns:
        List of sections in the specified range
    """
    sections = document.sections
    start_idx = 0
    end_idx = len(sections)

    if start_heading:
        for i, section in enumerate(sections):
            if start_heading.lower() in section.heading.lower():
                start_idx = i
                break

    if end_heading:
        for i, section in enumerate(sections):
            if end_heading.lower() in section.heading.lower():
                end_idx = i + 1
                break

    return sections[start_idx:end_idx]
