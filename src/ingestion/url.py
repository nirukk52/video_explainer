"""URL/web content parsing using httpx and BeautifulSoup."""

import re
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup, NavigableString

from ..models import ParsedDocument, Section, SourceType

# Default timeout for HTTP requests (seconds)
DEFAULT_TIMEOUT = 30.0

# User agent to identify as a browser
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def fetch_url_content(url: str, timeout: float = DEFAULT_TIMEOUT) -> str:
    """Fetch HTML content from a URL.

    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds

    Returns:
        HTML content as a string

    Raises:
        httpx.HTTPError: If the request fails
    """
    headers = {"User-Agent": DEFAULT_USER_AGENT}

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        response = client.get(url, headers=headers)
        response.raise_for_status()
        return response.text


def extract_title_from_html(soup: BeautifulSoup) -> str:
    """Extract the title from HTML content.

    Args:
        soup: BeautifulSoup parsed HTML

    Returns:
        Extracted title string
    """
    # Try <title> tag first
    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        return title_tag.string.strip()

    # Try <h1> tag
    h1_tag = soup.find("h1")
    if h1_tag:
        return h1_tag.get_text(strip=True)

    # Try og:title meta tag
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        return og_title["content"].strip()

    return "Untitled Page"


def clean_text(text: str) -> str:
    """Clean extracted text by normalizing whitespace.

    Args:
        text: Raw text to clean

    Returns:
        Cleaned text
    """
    # Replace multiple whitespace with single space
    text = re.sub(r"\s+", " ", text)
    # Remove leading/trailing whitespace
    text = text.strip()
    return text


def extract_main_content(soup: BeautifulSoup) -> BeautifulSoup:
    """Extract the main content area from HTML, removing navigation, ads, etc.

    Args:
        soup: BeautifulSoup parsed HTML

    Returns:
        BeautifulSoup object containing main content
    """
    # Remove unwanted elements
    unwanted_selectors = [
        "script",
        "style",
        "nav",
        "header",
        "footer",
        "aside",
        "iframe",
        "noscript",
        ".advertisement",
        ".ad",
        ".sidebar",
        ".navigation",
        ".nav",
        ".menu",
        ".footer",
        ".header",
        "#comments",
        ".comments",
        ".social-share",
        ".related-posts",
    ]

    for selector in unwanted_selectors:
        for element in soup.select(selector):
            element.decompose()

    # Try to find main content container
    main_content = None

    # Common main content selectors
    main_selectors = [
        "main",
        "article",
        '[role="main"]',
        ".post-content",
        ".article-content",
        ".entry-content",
        ".content",
        "#content",
        ".post",
        ".article",
    ]

    for selector in main_selectors:
        main_content = soup.select_one(selector)
        if main_content:
            break

    # If no main content found, use body
    if not main_content:
        main_content = soup.find("body")
        if not main_content:
            main_content = soup

    return main_content


def extract_code_blocks_from_html(soup: BeautifulSoup) -> list[str]:
    """Extract code blocks from HTML.

    Args:
        soup: BeautifulSoup object

    Returns:
        List of code block contents
    """
    code_blocks = []

    # Find <pre><code> blocks
    for pre in soup.find_all("pre"):
        code = pre.find("code")
        if code:
            code_blocks.append(code.get_text())
        else:
            # <pre> without <code>
            code_blocks.append(pre.get_text())

    # Find standalone <code> blocks that are substantial
    for code in soup.find_all("code"):
        # Skip if already inside a <pre>
        if code.find_parent("pre"):
            continue
        text = code.get_text()
        # Only include if it's substantial (multi-line or long)
        if "\n" in text or len(text) > 50:
            code_blocks.append(text)

    return code_blocks


def extract_images_from_html(soup: BeautifulSoup, base_url: str) -> list[str]:
    """Extract image URLs from HTML.

    Args:
        soup: BeautifulSoup object
        base_url: Base URL for resolving relative paths

    Returns:
        List of image URLs
    """
    images = []

    for img in soup.find_all("img"):
        src = img.get("src") or img.get("data-src")
        if src:
            # Resolve relative URLs
            full_url = urljoin(base_url, src)
            images.append(full_url)

    return images


def extract_equations_from_html(soup: BeautifulSoup) -> list[str]:
    """Extract equations from HTML (MathJax, KaTeX, etc.).

    Args:
        soup: BeautifulSoup object

    Returns:
        List of equation strings
    """
    equations = []

    # MathJax script tags
    for script in soup.find_all("script", {"type": "math/tex"}):
        if script.string:
            equations.append(script.string.strip())

    # KaTeX elements
    for katex in soup.find_all(class_=re.compile(r"katex|math")):
        # Try to get the source annotation
        annotation = katex.find("annotation", encoding="application/x-tex")
        if annotation and annotation.string:
            equations.append(annotation.string.strip())
        else:
            # Fallback to text content
            text = katex.get_text()
            if text and len(text) < 200:  # Reasonable equation length
                equations.append(text.strip())

    # Inline LaTeX patterns in text
    text = soup.get_text()
    inline_patterns = [
        r"\$\$(.+?)\$\$",
        r"\$([^$]+)\$",
        r"\\\[(.+?)\\\]",
        r"\\\((.+?)\\\)",
    ]
    for pattern in inline_patterns:
        matches = re.findall(pattern, text, re.DOTALL)
        equations.extend(matches)

    return equations


def split_html_into_sections(soup: BeautifulSoup) -> list[Section]:
    """Split HTML content into sections based on headings.

    Args:
        soup: BeautifulSoup main content object

    Returns:
        List of Section objects
    """
    sections = []

    # Find all headings
    headings = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])

    if not headings:
        # No headings found, treat entire content as one section
        content = soup.get_text(separator="\n", strip=True)
        return [
            Section(
                heading="Main Content",
                level=1,
                content=content,
                code_blocks=extract_code_blocks_from_html(soup),
                equations=extract_equations_from_html(soup),
                images=[],
            )
        ]

    # Process each heading
    for i, heading in enumerate(headings):
        heading_text = heading.get_text(strip=True)
        heading_level = int(heading.name[1])  # h1 -> 1, h2 -> 2, etc.

        # Collect content until next heading
        content_parts = []
        code_blocks = []
        equations = []

        current = heading.next_sibling
        while current:
            if current.name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                break

            if isinstance(current, NavigableString):
                text = str(current).strip()
                if text:
                    content_parts.append(text)
            elif current.name:
                # Extract code blocks from this element
                if current.name == "pre":
                    code = current.find("code")
                    if code:
                        code_blocks.append(code.get_text())
                    else:
                        code_blocks.append(current.get_text())
                else:
                    # Get text content
                    text = current.get_text(separator=" ", strip=True)
                    if text:
                        content_parts.append(text)

                    # Check for nested code
                    for pre in current.find_all("pre"):
                        code = pre.find("code")
                        if code:
                            code_blocks.append(code.get_text())
                        else:
                            code_blocks.append(pre.get_text())

            current = current.next_sibling

        content = "\n\n".join(content_parts)

        # Extract equations from content
        equations = []
        equation_patterns = [r"\$\$(.+?)\$\$", r"\$([^$]+)\$"]
        for pattern in equation_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            equations.extend(matches)

        sections.append(
            Section(
                heading=heading_text,
                level=heading_level,
                content=content,
                code_blocks=code_blocks,
                equations=equations,
                images=[],
            )
        )

    return sections


def parse_url(source: str) -> ParsedDocument:
    """Parse a web page into a structured document.

    Args:
        source: URL to fetch and parse

    Returns:
        ParsedDocument with extracted sections and metadata

    Raises:
        ValueError: If the URL is invalid
        httpx.HTTPError: If the request fails
    """
    # Validate URL
    parsed = urlparse(source)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid URL: {source}")

    # Ensure HTTPS (upgrade HTTP if needed)
    if parsed.scheme == "http":
        source = source.replace("http://", "https://", 1)

    # Fetch the content
    html_content = fetch_url_content(source)

    # Parse HTML
    soup = BeautifulSoup(html_content, "html.parser")

    # Extract title
    title = extract_title_from_html(soup)

    # Extract main content
    main_content = extract_main_content(soup)

    # Get raw text content
    raw_content = main_content.get_text(separator="\n", strip=True)

    # Split into sections
    sections = split_html_into_sections(main_content)

    # Extract images
    all_images = extract_images_from_html(main_content, source)

    # Add images to first section if available
    if sections and all_images:
        sections[0].images = all_images

    # Build metadata
    metadata = {
        "total_sections": len(sections),
        "total_code_blocks": sum(len(s.code_blocks) for s in sections),
        "total_equations": sum(len(s.equations) for s in sections),
        "total_images": len(all_images),
        "url": source,
        "domain": parsed.netloc,
    }

    # Extract additional meta info
    description_tag = soup.find("meta", {"name": "description"})
    if description_tag and description_tag.get("content"):
        metadata["description"] = description_tag["content"]

    author_tag = soup.find("meta", {"name": "author"})
    if author_tag and author_tag.get("content"):
        metadata["author"] = author_tag["content"]

    return ParsedDocument(
        title=title,
        source_type=SourceType.URL,
        source_path=source,
        sections=sections,
        raw_content=raw_content,
        metadata=metadata,
    )
