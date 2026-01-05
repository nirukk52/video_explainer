"""Tests for URL/web content parsing module."""

from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from src.ingestion import parse_document, parse_url
from src.ingestion.url import (
    clean_text,
    extract_code_blocks_from_html,
    extract_equations_from_html,
    extract_images_from_html,
    extract_main_content,
    extract_title_from_html,
    fetch_url_content,
    split_html_into_sections,
)
from src.models import SourceType


class TestExtractTitleFromHtml:
    """Tests for HTML title extraction."""

    def test_extracts_title_tag(self):
        """Should extract title from <title> tag."""
        html = "<html><head><title>Page Title</title></head><body></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        assert extract_title_from_html(soup) == "Page Title"

    def test_strips_whitespace_from_title(self):
        """Should strip whitespace from title."""
        html = "<html><head><title>  Spaced Title  </title></head></html>"
        soup = BeautifulSoup(html, "html.parser")
        assert extract_title_from_html(soup) == "Spaced Title"

    def test_fallback_to_h1(self):
        """Should fallback to h1 when no title tag."""
        html = "<html><body><h1>H1 Title</h1><p>Content</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        assert extract_title_from_html(soup) == "H1 Title"

    def test_fallback_to_og_title(self):
        """Should fallback to og:title meta tag."""
        html = """<html><head><meta property="og:title" content="OG Title"></head>
                  <body><p>Content</p></body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        assert extract_title_from_html(soup) == "OG Title"

    def test_returns_untitled_when_no_title_found(self):
        """Should return 'Untitled Page' when no title found."""
        html = "<html><body><p>Just content</p></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        assert extract_title_from_html(soup) == "Untitled Page"


class TestCleanText:
    """Tests for text cleaning."""

    def test_normalizes_whitespace(self):
        """Should normalize multiple spaces to single space."""
        text = "Hello    world   here"
        assert clean_text(text) == "Hello world here"

    def test_normalizes_newlines(self):
        """Should normalize newlines to spaces."""
        text = "Hello\n\n\nworld"
        assert clean_text(text) == "Hello world"

    def test_strips_leading_trailing(self):
        """Should strip leading and trailing whitespace."""
        text = "   content   "
        assert clean_text(text) == "content"

    def test_handles_empty_string(self):
        """Should handle empty strings."""
        assert clean_text("") == ""


class TestExtractMainContent:
    """Tests for main content extraction."""

    def test_removes_script_tags(self):
        """Should remove script tags."""
        html = """<html><body>
            <script>alert('hi')</script>
            <p>Content</p>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        main = extract_main_content(soup)
        assert main.find("script") is None
        assert "Content" in main.get_text()

    def test_removes_style_tags(self):
        """Should remove style tags."""
        html = """<html><body>
            <style>.foo { color: red; }</style>
            <p>Content</p>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        main = extract_main_content(soup)
        assert main.find("style") is None

    def test_removes_navigation(self):
        """Should remove nav elements."""
        html = """<html><body>
            <nav><a href="/">Home</a></nav>
            <main><p>Main content</p></main>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        main = extract_main_content(soup)
        assert main.find("nav") is None
        assert "Main content" in main.get_text()

    def test_finds_main_element(self):
        """Should return main element when present."""
        html = """<html><body>
            <header>Header</header>
            <main><p>Main content</p></main>
            <footer>Footer</footer>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        main = extract_main_content(soup)
        assert "Main content" in main.get_text()

    def test_finds_article_element(self):
        """Should find article element when no main."""
        html = """<html><body>
            <article><p>Article content</p></article>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        main = extract_main_content(soup)
        assert "Article content" in main.get_text()

    def test_fallback_to_body(self):
        """Should fallback to body when no main/article."""
        html = """<html><body>
            <div><p>Body content</p></div>
        </body></html>"""
        soup = BeautifulSoup(html, "html.parser")
        main = extract_main_content(soup)
        assert "Body content" in main.get_text()


class TestExtractCodeBlocksFromHtml:
    """Tests for code block extraction from HTML."""

    def test_extracts_pre_code_blocks(self):
        """Should extract code from pre>code elements."""
        html = """<div>
            <pre><code>def hello():
    return "world"</code></pre>
        </div>"""
        soup = BeautifulSoup(html, "html.parser")
        blocks = extract_code_blocks_from_html(soup)
        assert len(blocks) == 1
        assert "def hello():" in blocks[0]

    def test_extracts_pre_without_code(self):
        """Should extract pre elements without code wrapper."""
        html = """<div>
            <pre>Some preformatted text</pre>
        </div>"""
        soup = BeautifulSoup(html, "html.parser")
        blocks = extract_code_blocks_from_html(soup)
        assert len(blocks) == 1
        assert "preformatted" in blocks[0]

    def test_extracts_multiple_code_blocks(self):
        """Should extract multiple code blocks."""
        html = """<div>
            <pre><code>block 1</code></pre>
            <pre><code>block 2</code></pre>
        </div>"""
        soup = BeautifulSoup(html, "html.parser")
        blocks = extract_code_blocks_from_html(soup)
        assert len(blocks) == 2

    def test_extracts_substantial_inline_code(self):
        """Should extract substantial inline code blocks."""
        html = """<div>
            <code>short</code>
            <code>This is a longer code block that spans multiple
lines and contains significant content</code>
        </div>"""
        soup = BeautifulSoup(html, "html.parser")
        blocks = extract_code_blocks_from_html(soup)
        # Only the longer one should be extracted
        assert len(blocks) >= 1

    def test_handles_no_code_blocks(self):
        """Should handle HTML with no code blocks."""
        html = "<div><p>Just text</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        blocks = extract_code_blocks_from_html(soup)
        assert blocks == []


class TestExtractImagesFromHtml:
    """Tests for image extraction from HTML."""

    def test_extracts_img_src(self):
        """Should extract image src attributes."""
        html = '<div><img src="/images/photo.jpg" alt="Photo"></div>'
        soup = BeautifulSoup(html, "html.parser")
        images = extract_images_from_html(soup, "https://example.com")
        assert len(images) == 1
        assert "example.com/images/photo.jpg" in images[0]

    def test_extracts_data_src(self):
        """Should extract data-src for lazy-loaded images."""
        html = '<div><img data-src="/lazy/image.png" alt="Lazy"></div>'
        soup = BeautifulSoup(html, "html.parser")
        images = extract_images_from_html(soup, "https://example.com")
        assert len(images) == 1
        assert "lazy/image.png" in images[0]

    def test_resolves_relative_urls(self):
        """Should resolve relative URLs to absolute."""
        html = '<div><img src="./images/relative.jpg"></div>'
        soup = BeautifulSoup(html, "html.parser")
        images = extract_images_from_html(soup, "https://example.com/page/")
        assert len(images) == 1
        assert images[0].startswith("https://")

    def test_handles_absolute_urls(self):
        """Should preserve absolute URLs."""
        html = '<div><img src="https://cdn.example.com/image.png"></div>'
        soup = BeautifulSoup(html, "html.parser")
        images = extract_images_from_html(soup, "https://example.com")
        assert len(images) == 1
        assert images[0] == "https://cdn.example.com/image.png"

    def test_extracts_multiple_images(self):
        """Should extract all images."""
        html = """<div>
            <img src="/img1.jpg">
            <img src="/img2.jpg">
            <img src="/img3.jpg">
        </div>"""
        soup = BeautifulSoup(html, "html.parser")
        images = extract_images_from_html(soup, "https://example.com")
        assert len(images) == 3


class TestExtractEquationsFromHtml:
    """Tests for equation extraction from HTML."""

    def test_extracts_inline_latex(self):
        """Should extract inline LaTeX equations."""
        html = "<p>The equation is $E = mc^2$ in physics.</p>"
        soup = BeautifulSoup(html, "html.parser")
        equations = extract_equations_from_html(soup)
        assert "E = mc^2" in equations

    def test_extracts_block_latex(self):
        """Should extract block LaTeX equations."""
        html = "<p>$$\\int_0^1 x^2 dx$$</p>"
        soup = BeautifulSoup(html, "html.parser")
        equations = extract_equations_from_html(soup)
        assert len(equations) >= 1

    def test_extracts_mathjax_script(self):
        """Should extract MathJax script content."""
        html = '<script type="math/tex">x^2 + y^2 = r^2</script>'
        soup = BeautifulSoup(html, "html.parser")
        equations = extract_equations_from_html(soup)
        assert any("x^2" in eq for eq in equations)

    def test_handles_no_equations(self):
        """Should handle HTML with no equations."""
        html = "<p>Just plain text</p>"
        soup = BeautifulSoup(html, "html.parser")
        equations = extract_equations_from_html(soup)
        assert isinstance(equations, list)


class TestSplitHtmlIntoSections:
    """Tests for HTML section splitting."""

    def test_splits_by_headings(self):
        """Should split content by heading elements."""
        html = """<div>
            <h1>Introduction</h1>
            <p>Intro content</p>
            <h2>Methods</h2>
            <p>Methods content</p>
            <h2>Results</h2>
            <p>Results content</p>
        </div>"""
        soup = BeautifulSoup(html, "html.parser")
        sections = split_html_into_sections(soup)
        assert len(sections) >= 3
        headings = [s.heading for s in sections]
        assert "Introduction" in headings
        assert "Methods" in headings
        assert "Results" in headings

    def test_assigns_heading_levels(self):
        """Should assign correct heading levels."""
        html = """<div>
            <h1>Level 1</h1>
            <p>Content</p>
            <h2>Level 2</h2>
            <p>Content</p>
            <h3>Level 3</h3>
            <p>Content</p>
        </div>"""
        soup = BeautifulSoup(html, "html.parser")
        sections = split_html_into_sections(soup)

        level1 = next((s for s in sections if s.heading == "Level 1"), None)
        level2 = next((s for s in sections if s.heading == "Level 2"), None)
        level3 = next((s for s in sections if s.heading == "Level 3"), None)

        assert level1.level == 1
        assert level2.level == 2
        assert level3.level == 3

    def test_extracts_section_content(self):
        """Should extract content between headings."""
        html = """<div>
            <h2>Section One</h2>
            <p>Paragraph one</p>
            <p>Paragraph two</p>
            <h2>Section Two</h2>
            <p>Different content</p>
        </div>"""
        soup = BeautifulSoup(html, "html.parser")
        sections = split_html_into_sections(soup)

        section_one = next((s for s in sections if s.heading == "Section One"), None)
        assert section_one is not None
        assert "Paragraph one" in section_one.content
        assert "Paragraph two" in section_one.content

    def test_handles_no_headings(self):
        """Should create single section when no headings."""
        html = "<div><p>Just content without headings</p></div>"
        soup = BeautifulSoup(html, "html.parser")
        sections = split_html_into_sections(soup)
        assert len(sections) == 1
        assert sections[0].heading == "Main Content"

    def test_extracts_code_blocks_in_sections(self):
        """Should extract code blocks within sections."""
        html = """<div>
            <h2>Code Section</h2>
            <pre><code>def example(): pass</code></pre>
        </div>"""
        soup = BeautifulSoup(html, "html.parser")
        sections = split_html_into_sections(soup)
        assert len(sections[0].code_blocks) >= 1


class TestFetchUrlContent:
    """Tests for URL fetching."""

    @patch("src.ingestion.url.httpx.Client")
    def test_fetches_url_content(self, mock_client_class):
        """Should fetch and return HTML content."""
        mock_response = MagicMock()
        mock_response.text = "<html><body>Content</body></html>"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        content = fetch_url_content("https://example.com")
        assert "Content" in content

    @patch("src.ingestion.url.httpx.Client")
    def test_uses_user_agent(self, mock_client_class):
        """Should use a browser-like user agent."""
        mock_response = MagicMock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        fetch_url_content("https://example.com")
        call_args = mock_client.get.call_args
        headers = call_args.kwargs.get("headers", {})
        assert "User-Agent" in headers
        assert "Mozilla" in headers["User-Agent"]


class TestParseUrl:
    """Tests for the main parse_url function."""

    def test_raises_for_invalid_url(self):
        """Should raise ValueError for invalid URLs."""
        with pytest.raises(ValueError, match="Invalid URL"):
            parse_url("not-a-valid-url")

    def test_raises_for_missing_scheme(self):
        """Should raise ValueError for URLs without scheme."""
        with pytest.raises(ValueError, match="Invalid URL"):
            parse_url("example.com/page")

    @patch("src.ingestion.url.fetch_url_content")
    def test_parses_simple_html(self, mock_fetch):
        """Should parse simple HTML content."""
        mock_fetch.return_value = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <main>
                    <h1>Welcome</h1>
                    <p>Content here</p>
                </main>
            </body>
        </html>
        """

        result = parse_url("https://example.com/page")
        assert result.title == "Test Page"
        assert result.source_type == SourceType.URL
        assert len(result.sections) >= 1

    @patch("src.ingestion.url.fetch_url_content")
    def test_extracts_metadata(self, mock_fetch):
        """Should extract metadata from URL result."""
        mock_fetch.return_value = """
        <html>
            <head>
                <title>Meta Test</title>
                <meta name="description" content="Page description">
                <meta name="author" content="Test Author">
            </head>
            <body><p>Content</p></body>
        </html>
        """

        result = parse_url("https://example.com/meta")
        assert result.metadata["domain"] == "example.com"
        assert result.metadata["description"] == "Page description"
        assert result.metadata["author"] == "Test Author"

    @patch("src.ingestion.url.fetch_url_content")
    def test_extracts_code_blocks(self, mock_fetch):
        """Should extract code blocks from page."""
        mock_fetch.return_value = """
        <html>
            <body>
                <h1>Code Example</h1>
                <pre><code>def hello(): return "world"</code></pre>
            </body>
        </html>
        """

        result = parse_url("https://example.com/code")
        total_code = sum(len(s.code_blocks) for s in result.sections)
        assert total_code >= 1

    @patch("src.ingestion.url.fetch_url_content")
    def test_extracts_images(self, mock_fetch):
        """Should extract images from page."""
        mock_fetch.return_value = """
        <html>
            <body>
                <h1>Image Test</h1>
                <img src="/images/photo.jpg">
                <img src="/images/diagram.png">
            </body>
        </html>
        """

        result = parse_url("https://example.com/images")
        assert result.metadata["total_images"] >= 2

    @patch("src.ingestion.url.fetch_url_content")
    def test_upgrades_http_to_https(self, mock_fetch):
        """Should upgrade HTTP to HTTPS."""
        mock_fetch.return_value = "<html><body>Content</body></html>"

        result = parse_url("http://example.com/page")
        assert result.source_path.startswith("https://")

    @patch("src.ingestion.url.fetch_url_content")
    def test_stores_url_in_source_path(self, mock_fetch):
        """Should store URL in source_path."""
        mock_fetch.return_value = "<html><body>Content</body></html>"

        result = parse_url("https://example.com/page")
        assert result.source_path == "https://example.com/page"

    @patch("src.ingestion.url.fetch_url_content")
    def test_extracts_raw_content(self, mock_fetch):
        """Should extract raw text content."""
        mock_fetch.return_value = """
        <html>
            <body>
                <p>First paragraph with content.</p>
                <p>Second paragraph here.</p>
            </body>
        </html>
        """

        result = parse_url("https://example.com/content")
        assert "First paragraph" in result.raw_content
        assert "Second paragraph" in result.raw_content


class TestParseDocumentUrl:
    """Tests for parse_document with URLs."""

    @patch("src.ingestion.url.fetch_url_content")
    def test_parses_url_via_parse_document(self, mock_fetch):
        """Should correctly route URLs through parse_document."""
        mock_fetch.return_value = """
        <html>
            <head><title>URL via Main</title></head>
            <body><p>Content</p></body>
        </html>
        """

        result = parse_document("https://example.com/page")
        assert result.source_type == SourceType.URL
        assert result.title == "URL via Main"

    def test_detects_url_source_type(self):
        """Should detect URL source type correctly."""
        from src.ingestion.parser import detect_source_type

        assert detect_source_type("https://example.com") == SourceType.URL
        assert detect_source_type("http://example.com") == SourceType.URL
        assert detect_source_type("https://example.com/path/to/page") == SourceType.URL

    def test_does_not_detect_non_urls(self):
        """Should not detect non-URLs as URL type."""
        from src.ingestion.parser import detect_source_type

        # Plain text should not be detected as URL
        assert detect_source_type("just some text") != SourceType.URL
        assert detect_source_type("file.md") != SourceType.URL


class TestRealWorldUrl:
    """Integration tests with real URLs (marked as slow)."""

    @pytest.mark.slow
    def test_parses_real_webpage(self):
        """Should parse a real webpage (requires network)."""
        # Using a stable, well-structured page
        result = parse_url("https://example.com")
        assert result.title is not None
        assert result.source_type == SourceType.URL
        assert len(result.raw_content) > 0
