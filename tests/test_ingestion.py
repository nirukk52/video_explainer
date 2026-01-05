"""Tests for content ingestion module."""

from pathlib import Path

import pytest

from src.ingestion import parse_document, parse_markdown
from src.ingestion.markdown import (
    extract_code_blocks,
    extract_equations,
    extract_images,
    extract_title,
    split_into_sections,
)
from src.models import SourceType


class TestExtractTitle:
    """Tests for title extraction."""

    def test_extracts_h1_title(self):
        content = "# My Great Title\n\nSome content here."
        assert extract_title(content) == "My Great Title"

    def test_extracts_h1_with_leading_content(self):
        content = "Some preamble\n\n# The Real Title\n\nContent"
        assert extract_title(content) == "The Real Title"

    def test_fallback_to_first_line(self):
        content = "Just a plain document\n\nWith no headers"
        assert extract_title(content) == "Just a plain document"


class TestExtractCodeBlocks:
    """Tests for code block extraction."""

    def test_extracts_single_code_block(self):
        content = """
Some text here.

```python
def hello():
    return "world"
```

More text.
"""
        blocks = extract_code_blocks(content)
        assert len(blocks) == 1
        assert "def hello():" in blocks[0]

    def test_extracts_multiple_code_blocks(self):
        content = """
```javascript
const x = 1;
```

Some text.

```python
x = 1
```
"""
        blocks = extract_code_blocks(content)
        assert len(blocks) == 2

    def test_handles_no_code_blocks(self):
        content = "Just plain text."
        assert extract_code_blocks(content) == []


class TestExtractEquations:
    """Tests for equation extraction."""

    def test_extracts_inline_equations(self):
        content = "The formula is $E = mc^2$ and also $F = ma$."
        equations = extract_equations(content)
        assert "E = mc^2" in equations
        assert "F = ma" in equations

    def test_extracts_block_equations(self):
        content = """
The big equation is:

$$
\\int_0^\\infty e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}
$$
"""
        equations = extract_equations(content)
        assert len(equations) >= 1

    def test_handles_no_equations(self):
        content = "No math here."
        assert extract_equations(content) == []


class TestExtractImages:
    """Tests for image extraction."""

    def test_extracts_image_paths(self):
        content = "Here is an image: ![Alt text](images/diagram.png)"
        images = extract_images(content)
        assert images == ["images/diagram.png"]

    def test_extracts_multiple_images(self):
        content = """
![First](a.png)
![Second](b.jpg)
"""
        images = extract_images(content)
        assert len(images) == 2
        assert "a.png" in images
        assert "b.jpg" in images


class TestSplitIntoSections:
    """Tests for section splitting."""

    def test_splits_by_headings(self):
        content = """
# Main Title

Introduction text.

## Section One

Content of section one.

## Section Two

Content of section two.

### Subsection

Nested content.
"""
        sections = split_into_sections(content)
        assert len(sections) == 4
        assert sections[0].heading == "Main Title"
        assert sections[0].level == 1
        assert sections[1].heading == "Section One"
        assert sections[1].level == 2
        assert sections[3].heading == "Subsection"
        assert sections[3].level == 3

    def test_handles_no_headings(self):
        content = "Just some plain text without any headings."
        sections = split_into_sections(content)
        assert len(sections) == 1
        assert sections[0].heading == "Main"

    def test_extracts_code_in_sections(self):
        content = """
## Code Section

Here is some code:

```python
x = 1
```
"""
        sections = split_into_sections(content)
        assert len(sections[0].code_blocks) == 1


class TestParseMarkdown:
    """Tests for full markdown parsing."""

    def test_parses_markdown_string(self):
        content = """
# Test Document

This is a test.

## First Section

Some content with $E=mc^2$ math.

```python
print("hello")
```

## Second Section

More content.
"""
        doc = parse_markdown(content)
        assert doc.title == "Test Document"
        assert doc.source_type == SourceType.MARKDOWN
        assert len(doc.sections) == 3
        assert doc.metadata["total_sections"] == 3
        assert doc.metadata["total_code_blocks"] == 1
        assert doc.metadata["total_equations"] >= 1

    def test_parses_markdown_file(self, tmp_path):
        # Create a temporary markdown file
        md_file = tmp_path / "test.md"
        md_file.write_text("# File Title\n\nContent here.")

        doc = parse_markdown(md_file)
        assert doc.title == "File Title"
        assert doc.source_path == str(md_file.absolute())


class TestParseDocument:
    """Tests for main document parser."""

    def test_parses_markdown_string(self):
        content = "# Hello\n\nWorld"
        doc = parse_document(content)
        assert doc.title == "Hello"
        assert doc.source_type == SourceType.MARKDOWN

    def test_parses_markdown_file(self, tmp_path):
        md_file = tmp_path / "doc.md"
        md_file.write_text("# From File\n\nContent")

        doc = parse_document(md_file)
        assert doc.title == "From File"

    def test_raises_for_invalid_pdf(self, tmp_path):
        """Should raise ValueError for invalid PDF content."""
        pdf_file = tmp_path / "doc.pdf"
        pdf_file.write_text("fake pdf content")

        with pytest.raises(ValueError, match="Failed to open PDF"):
            parse_document(pdf_file)


class TestRealDocument:
    """Test parsing the actual LLM inference document."""

    @pytest.fixture
    def inference_doc_path(self):
        path = Path("/Users/prajwal/Desktop/Learning/inference/website/post.md")
        if not path.exists():
            pytest.skip("Inference document not found")
        return path

    def test_parses_inference_document(self, inference_doc_path):
        doc = parse_document(inference_doc_path)

        # Verify basic structure
        assert doc.title == "Scaling LLM Inference to Millions of Users"
        assert len(doc.sections) > 5

        # Check for expected sections
        section_headings = [s.heading for s in doc.sections]
        assert any("Two Phases" in h for h in section_headings)
        assert any("KV Cache" in h or "vLLM" in h for h in section_headings)

        # Check for code blocks and equations
        assert doc.metadata["total_code_blocks"] > 0
        assert doc.metadata["total_equations"] > 0

    def test_extracts_specific_sections(self, inference_doc_path):
        from src.ingestion.parser import extract_sections_by_range

        doc = parse_document(inference_doc_path)
        sections = extract_sections_by_range(
            doc,
            start_heading="Two Phases",
            end_heading="Enter vLLM",
        )

        assert len(sections) >= 2
        assert any("Prefill" in s.content for s in sections)
        assert any("Decode" in s.content for s in sections)
