"""Tests for PDF parsing module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.ingestion import parse_document, parse_pdf
from src.ingestion.pdf import (
    detect_headings_in_text,
    extract_code_patterns,
    extract_equation_patterns,
    extract_images_from_pdf,
    extract_text_from_pdf,
    extract_title_from_pdf,
    split_pdf_into_sections,
)
from src.models import SourceType


class TestExtractTitleFromPdf:
    """Tests for PDF title extraction."""

    def test_extracts_title_from_metadata(self):
        """Should extract title from PDF metadata."""
        mock_doc = MagicMock()
        mock_doc.metadata = {"title": "Test Document Title"}
        mock_doc.__len__ = lambda x: 1

        title = extract_title_from_pdf(mock_doc)
        assert title == "Test Document Title"

    def test_strips_whitespace_from_title(self):
        """Should strip whitespace from extracted title."""
        mock_doc = MagicMock()
        mock_doc.metadata = {"title": "  Padded Title  "}
        mock_doc.__len__ = lambda x: 1

        title = extract_title_from_pdf(mock_doc)
        assert title == "Padded Title"

    def test_fallback_to_first_page_content(self):
        """Should fallback to first page content when no metadata title."""
        mock_doc = MagicMock()
        mock_doc.metadata = {}
        mock_doc.__len__ = lambda x: 1

        mock_page = MagicMock()
        mock_page.get_text.return_value = "First Line Title\n\nSome content here."
        mock_doc.__getitem__ = lambda x, i: mock_page

        title = extract_title_from_pdf(mock_doc)
        assert title == "First Line Title"

    def test_truncates_long_titles(self):
        """Should truncate titles longer than 100 characters."""
        mock_doc = MagicMock()
        mock_doc.metadata = {}
        mock_doc.__len__ = lambda x: 1

        long_title = "A" * 150
        mock_page = MagicMock()
        mock_page.get_text.return_value = f"{long_title}\n\nContent"
        mock_doc.__getitem__ = lambda x, i: mock_page

        title = extract_title_from_pdf(mock_doc)
        assert len(title) == 100

    def test_returns_untitled_for_empty_doc(self):
        """Should return 'Untitled Document' for empty documents."""
        mock_doc = MagicMock()
        mock_doc.metadata = {}
        mock_doc.__len__ = lambda x: 0

        title = extract_title_from_pdf(mock_doc)
        assert title == "Untitled Document"


class TestExtractImagesFromPdf:
    """Tests for PDF image extraction."""

    def test_extracts_images_from_pages(self):
        """Should extract images from all pages."""
        mock_doc = MagicMock()
        mock_doc.__len__ = lambda x: 2

        mock_page1 = MagicMock()
        mock_page1.get_images.return_value = [("img1",), ("img2",)]

        mock_page2 = MagicMock()
        mock_page2.get_images.return_value = [("img3",)]

        mock_doc.__getitem__ = lambda x, i: mock_page1 if i == 0 else mock_page2

        images = extract_images_from_pdf(mock_doc)
        assert len(images) == 3
        assert "page1_img1" in images
        assert "page1_img2" in images
        assert "page2_img1" in images

    def test_handles_no_images(self):
        """Should handle documents with no images."""
        mock_doc = MagicMock()
        mock_doc.__len__ = lambda x: 1

        mock_page = MagicMock()
        mock_page.get_images.return_value = []
        mock_doc.__getitem__ = lambda x, i: mock_page

        images = extract_images_from_pdf(mock_doc)
        assert images == []


class TestDetectHeadingsInText:
    """Tests for heading detection in PDF text."""

    def test_detects_uppercase_headings(self):
        """Should detect all-caps headings."""
        text = """INTRODUCTION

This is the introduction paragraph.

METHODS

This is the methods section."""

        headings = detect_headings_in_text(text)
        heading_texts = [h[0] for h in headings]
        assert "INTRODUCTION" in heading_texts
        assert "METHODS" in heading_texts

    def test_detects_numbered_sections(self):
        """Should detect numbered section headings."""
        text = """1. Introduction

This is the intro.

2.1 Background

Some background info.

2.1.1 Historical Context

More details."""

        headings = detect_headings_in_text(text)
        heading_texts = [h[0] for h in headings]
        assert "1. Introduction" in heading_texts
        assert "2.1 Background" in heading_texts

    def test_detects_title_case_headings(self):
        """Should detect title case short lines as headings."""
        text = """The Main Topic

This paragraph explains the main topic in detail with lots of words
that span multiple lines and provide detailed information.

Another Section

More content here."""

        headings = detect_headings_in_text(text)
        heading_texts = [h[0] for h in headings]
        assert "The Main Topic" in heading_texts
        assert "Another Section" in heading_texts

    def test_ignores_long_lines(self):
        """Should not detect very long lines as headings."""
        text = """This is a very long line that should not be detected as a heading because it is too long to be a reasonable heading

Short Heading

Content here."""

        headings = detect_headings_in_text(text)
        heading_texts = [h[0] for h in headings]
        # The long line should not be detected
        assert len([h for h in heading_texts if len(h) > 100]) == 0

    def test_handles_empty_text(self):
        """Should handle empty text gracefully."""
        headings = detect_headings_in_text("")
        assert headings == []


class TestExtractCodePatterns:
    """Tests for code pattern extraction from PDF text."""

    def test_extracts_indented_code(self):
        """Should extract code blocks indented by 4+ spaces."""
        text = """Some explanation:

    def hello():
        return "world"

More text."""

        code_blocks = extract_code_patterns(text)
        assert len(code_blocks) >= 1
        assert any("def hello():" in block for block in code_blocks)

    def test_extracts_python_keywords(self):
        """Should detect Python code patterns."""
        text = """Here is some code:

def my_function(x):
    if x > 0:
        return x
    return 0

End of code."""

        code_blocks = extract_code_patterns(text)
        assert len(code_blocks) >= 1

    def test_extracts_javascript_keywords(self):
        """Should detect JavaScript code patterns."""
        text = """JavaScript example:

const x = 1;
function test() {
    let y = x + 1;
    return y;
}

Done."""

        code_blocks = extract_code_patterns(text)
        assert len(code_blocks) >= 1

    def test_ignores_single_line_code(self):
        """Should not extract single lines as code blocks."""
        text = """Some text with a = b + c; in it.

Normal paragraph here."""

        code_blocks = extract_code_patterns(text)
        # Single line code-like content should be ignored
        assert len(code_blocks) == 0

    def test_handles_no_code(self):
        """Should handle text with no code."""
        text = "Just plain text without any code."
        code_blocks = extract_code_patterns(text)
        assert code_blocks == []


class TestExtractEquationPatterns:
    """Tests for equation extraction from PDF text."""

    def test_extracts_latex_inline_equations(self):
        """Should extract inline LaTeX equations."""
        text = "The formula is $E = mc^2$ and the energy."
        equations = extract_equation_patterns(text)
        assert "E = mc^2" in equations

    def test_extracts_latex_block_equations(self):
        """Should extract block LaTeX equations."""
        text = """The integral is:

$$\\int_0^1 x^2 dx$$

Which equals..."""

        equations = extract_equation_patterns(text)
        assert len(equations) >= 1

    def test_extracts_function_notation(self):
        """Should extract function notation patterns."""
        text = "We define f(x) = 2x + 1 as our function."
        equations = extract_equation_patterns(text)
        assert any("f(x)" in eq for eq in equations)

    def test_handles_no_equations(self):
        """Should handle text with no equations."""
        text = "Plain text without math."
        equations = extract_equation_patterns(text)
        # May be empty or have some false positives, but shouldn't crash
        assert isinstance(equations, list)


class TestSplitPdfIntoSections:
    """Tests for PDF section splitting."""

    def test_splits_by_detected_headings(self):
        """Should split content by detected headings."""
        text = """INTRODUCTION

This is the introduction with some content.

METHODS

Here are the methods we used.

RESULTS

The results show..."""

        sections = split_pdf_into_sections(text)
        assert len(sections) >= 3
        headings = [s.heading for s in sections]
        assert "INTRODUCTION" in headings
        assert "METHODS" in headings
        assert "RESULTS" in headings

    def test_handles_no_headings(self):
        """Should create single section when no headings found."""
        text = "Just some plain text without any clear headings."
        sections = split_pdf_into_sections(text)
        assert len(sections) == 1
        assert sections[0].heading == "Main Content"

    def test_assigns_heading_levels(self):
        """Should assign appropriate heading levels."""
        text = """MAIN HEADING

Content here.

1.1 Subsection

More content."""

        sections = split_pdf_into_sections(text)
        # All caps should be level 1
        main_section = next((s for s in sections if s.heading == "MAIN HEADING"), None)
        if main_section:
            assert main_section.level == 1

    def test_extracts_section_content(self):
        """Should extract content between headings."""
        text = """INTRODUCTION

This is the introduction paragraph with detailed information.

CONCLUSION

Final thoughts here."""

        sections = split_pdf_into_sections(text)
        intro = next((s for s in sections if s.heading == "INTRODUCTION"), None)
        assert intro is not None
        assert "introduction paragraph" in intro.content


class TestParsePdf:
    """Tests for the main parse_pdf function."""

    def test_raises_for_nonexistent_file(self):
        """Should raise FileNotFoundError for missing files."""
        with pytest.raises(FileNotFoundError):
            parse_pdf("/nonexistent/path/document.pdf")

    def test_raises_for_non_pdf_file(self, tmp_path):
        """Should raise ValueError for non-PDF files."""
        txt_file = tmp_path / "document.txt"
        txt_file.write_text("Just text")

        with pytest.raises(ValueError, match="not a PDF"):
            parse_pdf(txt_file)

    def test_accepts_path_object(self, tmp_path):
        """Should accept Path objects."""
        # Create a minimal PDF using PyMuPDF
        import fitz

        pdf_path = tmp_path / "test.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Test Document\n\nThis is test content.")
        doc.save(str(pdf_path))
        doc.close()

        result = parse_pdf(pdf_path)
        assert result.source_type == SourceType.PDF

    def test_accepts_string_path(self, tmp_path):
        """Should accept string paths."""
        import fitz

        pdf_path = tmp_path / "test.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "String Path Test")
        doc.save(str(pdf_path))
        doc.close()

        result = parse_pdf(str(pdf_path))
        assert result.source_type == SourceType.PDF

    def test_extracts_document_structure(self, tmp_path):
        """Should extract complete document structure."""
        import fitz

        pdf_path = tmp_path / "structured.pdf"
        doc = fitz.open()

        # Create a page with content
        page = doc.new_page()
        content = """INTRODUCTION

This is the introduction.

METHODS

These are the methods with $E = mc^2$ equation."""
        page.insert_text((72, 72), content)
        doc.set_metadata({"title": "Test Document"})
        doc.save(str(pdf_path))
        doc.close()

        result = parse_pdf(pdf_path)
        assert result.title == "Test Document"
        assert result.source_type == SourceType.PDF
        assert len(result.sections) >= 1
        assert "total_sections" in result.metadata
        assert "page_count" in result.metadata

    def test_includes_pdf_metadata(self, tmp_path):
        """Should include PDF metadata in result."""
        import fitz

        pdf_path = tmp_path / "metadata.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Content")
        doc.set_metadata({
            "title": "Metadata Test",
            "author": "Test Author",
            "subject": "Testing",
        })
        doc.save(str(pdf_path))
        doc.close()

        result = parse_pdf(pdf_path)
        assert result.metadata["pdf_author"] == "Test Author"
        assert result.metadata["pdf_subject"] == "Testing"

    def test_handles_multi_page_pdf(self, tmp_path):
        """Should handle multi-page PDFs."""
        import fitz

        pdf_path = tmp_path / "multipage.pdf"
        doc = fitz.open()

        for i in range(3):
            page = doc.new_page()
            page.insert_text((72, 72), f"Page {i + 1} content")

        doc.save(str(pdf_path))
        doc.close()

        result = parse_pdf(pdf_path)
        assert result.metadata["page_count"] == 3

    def test_extracts_raw_content(self, tmp_path):
        """Should extract all text as raw_content."""
        import fitz

        pdf_path = tmp_path / "rawcontent.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Test raw content extraction")
        doc.save(str(pdf_path))
        doc.close()

        result = parse_pdf(pdf_path)
        assert "raw content extraction" in result.raw_content


class TestParseDocumentPdf:
    """Tests for parse_document with PDF files."""

    def test_parses_pdf_via_parse_document(self, tmp_path):
        """Should correctly route PDF files through parse_document."""
        import fitz

        pdf_path = tmp_path / "via_main.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Via Main Parser")
        doc.save(str(pdf_path))
        doc.close()

        result = parse_document(pdf_path)
        assert result.source_type == SourceType.PDF

    def test_detects_pdf_source_type(self, tmp_path):
        """Should detect PDF source type correctly."""
        import fitz
        from src.ingestion.parser import detect_source_type

        pdf_path = tmp_path / "detect.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Detection Test")
        doc.save(str(pdf_path))
        doc.close()

        source_type = detect_source_type(pdf_path)
        assert source_type == SourceType.PDF
