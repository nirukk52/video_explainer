"""PDF document parsing using PyMuPDF."""

import re
from pathlib import Path

import fitz  # PyMuPDF

from ..models import ParsedDocument, Section, SourceType


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract all text content from a PDF file.

    Args:
        pdf_path: Path to the PDF file

    Returns:
        Extracted text content as a string
    """
    doc = fitz.open(pdf_path)
    text_parts = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        if text.strip():
            text_parts.append(text)

    doc.close()
    return "\n\n".join(text_parts)


def extract_title_from_pdf(doc: fitz.Document) -> str:
    """Extract the title from PDF metadata or first page content.

    Args:
        doc: PyMuPDF document object

    Returns:
        Extracted title string
    """
    # Try metadata first
    metadata = doc.metadata
    if metadata and metadata.get("title"):
        return metadata["title"].strip()

    # Fallback: extract from first page
    if len(doc) > 0:
        first_page = doc[0]
        text = first_page.get_text()
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if lines:
            # Return first non-empty line, truncated if too long
            title = lines[0]
            return title[:100] if len(title) > 100 else title

    return "Untitled Document"


def extract_images_from_pdf(doc: fitz.Document) -> list[str]:
    """Extract image references from a PDF.

    Args:
        doc: PyMuPDF document object

    Returns:
        List of image descriptions (page and index)
    """
    images = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        image_list = page.get_images()
        for img_idx, img in enumerate(image_list):
            images.append(f"page{page_num + 1}_img{img_idx + 1}")
    return images


def detect_headings_in_text(text: str) -> list[tuple[str, int]]:
    """Detect potential headings in extracted PDF text.

    Heuristics used:
    - Lines that are short (< 80 chars) and followed by longer content
    - Lines that are all caps or title case
    - Lines that end without punctuation

    Args:
        text: Extracted text content

    Returns:
        List of (heading_text, line_index) tuples
    """
    lines = text.split("\n")
    headings = []

    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        # Skip very long lines
        if len(line) > 100:
            continue

        # Check if it looks like a heading
        is_heading = False

        # All caps (likely a major heading)
        if line.isupper() and len(line) > 3:
            is_heading = True

        # Title case and short
        elif line.istitle() and len(line) < 60:
            is_heading = True

        # Numbered sections like "1. Introduction" or "1.1 Background"
        elif re.match(r"^\d+\.(\d+\.?)?\s+[A-Z]", line):
            is_heading = True

        # Lines that don't end with sentence punctuation
        elif (
            len(line) < 60
            and not line.endswith((".", ",", ";", ":", "?", "!"))
            and line[0].isupper()
        ):
            # Check if next non-empty line is longer (paragraph content)
            for j in range(i + 1, min(i + 5, len(lines))):
                next_line = lines[j].strip()
                if next_line and len(next_line) > len(line) * 1.5:
                    is_heading = True
                    break

        if is_heading:
            headings.append((line, i))

    return headings


def split_pdf_into_sections(text: str) -> list[Section]:
    """Split PDF text into sections based on detected headings.

    Args:
        text: Extracted PDF text

    Returns:
        List of Section objects
    """
    headings = detect_headings_in_text(text)
    lines = text.split("\n")
    sections = []

    if not headings:
        # No headings found, treat entire content as one section
        return [
            Section(
                heading="Main Content",
                level=1,
                content=text.strip(),
                code_blocks=extract_code_patterns(text),
                equations=extract_equation_patterns(text),
                images=[],
            )
        ]

    # Process each heading and its content
    for i, (heading, line_idx) in enumerate(headings):
        # Determine where this section ends
        if i + 1 < len(headings):
            end_idx = headings[i + 1][1]
        else:
            end_idx = len(lines)

        # Extract content between this heading and the next
        content_lines = lines[line_idx + 1 : end_idx]
        content = "\n".join(content_lines).strip()

        # Determine heading level based on formatting
        level = 1
        if heading.isupper():
            level = 1
        elif re.match(r"^\d+\.\d+", heading):
            level = 2
        elif re.match(r"^\d+\.\d+\.\d+", heading):
            level = 3
        else:
            level = 2

        sections.append(
            Section(
                heading=heading,
                level=level,
                content=content,
                code_blocks=extract_code_patterns(content),
                equations=extract_equation_patterns(content),
                images=[],
            )
        )

    return sections


def extract_code_patterns(text: str) -> list[str]:
    """Extract code-like patterns from PDF text.

    PDFs don't have markdown code blocks, so we look for:
    - Monospaced font indicators (not available in plain text)
    - Indented blocks
    - Lines with code-like syntax

    Args:
        text: Text content to analyze

    Returns:
        List of extracted code blocks
    """
    code_blocks = []
    lines = text.split("\n")
    current_block = []
    in_code_block = False

    for line in lines:
        # Detect code-like patterns
        is_code_line = False

        # Check for common code indicators
        if re.match(r"^\s{4,}", line):  # Indented by 4+ spaces
            is_code_line = True
        elif re.match(r".*[{}\[\]();=<>].*", line) and len(line) < 120:
            # Contains code-like characters
            is_code_line = True
        elif re.match(r"^(def |class |import |from |if |for |while |return )", line.strip()):
            # Python keywords
            is_code_line = True
        elif re.match(r"^(function |const |let |var |=>)", line.strip()):
            # JavaScript keywords
            is_code_line = True

        if is_code_line:
            if not in_code_block:
                in_code_block = True
            current_block.append(line)
        else:
            if in_code_block and current_block:
                # Save the block if it's substantial (more than 2 lines)
                if len(current_block) >= 2:
                    code_blocks.append("\n".join(current_block))
                current_block = []
                in_code_block = False

    # Don't forget the last block
    if current_block and len(current_block) >= 2:
        code_blocks.append("\n".join(current_block))

    return code_blocks


def extract_equation_patterns(text: str) -> list[str]:
    """Extract equation-like patterns from PDF text.

    Args:
        text: Text content to analyze

    Returns:
        List of extracted equations
    """
    equations = []

    # LaTeX-style equations (may appear in academic PDFs)
    latex_patterns = [
        r"\$\$(.+?)\$\$",  # Block equations
        r"\$([^$]+)\$",  # Inline equations
        r"\\begin\{equation\}(.+?)\\end\{equation\}",
        r"\\begin\{align\}(.+?)\\end\{align\}",
    ]

    for pattern in latex_patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        equations.extend(matches)

    # Mathematical expressions (simple pattern matching)
    # E.g., "x = y + z", "f(x) = ...", etc.
    math_pattern = r"([a-zA-Z]\([a-zA-Z]\)\s*=\s*[^.]+)"
    matches = re.findall(math_pattern, text)
    equations.extend(matches)

    return equations


def parse_pdf(source: str | Path) -> ParsedDocument:
    """Parse a PDF file into a structured document.

    Args:
        source: Path to the PDF file

    Returns:
        ParsedDocument with extracted sections and metadata

    Raises:
        FileNotFoundError: If the PDF file doesn't exist
        ValueError: If the file is not a valid PDF
    """
    path = Path(source) if isinstance(source, str) else source

    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {path}")

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"File is not a PDF: {path}")

    # Open the PDF
    try:
        doc = fitz.open(path)
    except Exception as e:
        raise ValueError(f"Failed to open PDF: {e}") from e

    try:
        # Extract title
        title = extract_title_from_pdf(doc)

        # Extract all text
        text_parts = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                text_parts.append(text)
        raw_content = "\n\n".join(text_parts)

        # Extract images
        all_images = extract_images_from_pdf(doc)

        # Split into sections
        sections = split_pdf_into_sections(raw_content)

        # Add images to appropriate sections or first section
        if sections and all_images:
            sections[0].images = all_images

        # Build metadata
        pdf_metadata = doc.metadata or {}
        metadata = {
            "total_sections": len(sections),
            "total_code_blocks": sum(len(s.code_blocks) for s in sections),
            "total_equations": sum(len(s.equations) for s in sections),
            "total_images": len(all_images),
            "page_count": len(doc),
            "pdf_author": pdf_metadata.get("author", ""),
            "pdf_subject": pdf_metadata.get("subject", ""),
            "pdf_creator": pdf_metadata.get("creator", ""),
        }

        return ParsedDocument(
            title=title,
            source_type=SourceType.PDF,
            source_path=str(path.absolute()),
            sections=sections,
            raw_content=raw_content,
            metadata=metadata,
        )

    finally:
        doc.close()
