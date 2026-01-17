"""Shared test fixtures."""

from pathlib import Path

import pytest

from src.config import Config


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--run-llm-tests",
        action="store_true",
        default=False,
        help="Run LLM integration tests (expensive, makes real API calls)",
    )


def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line(
        "markers", "llm_integration: mark test as requiring real LLM calls"
    )


def pytest_collection_modifyitems(config, items):
    """Skip LLM tests unless --run-llm-tests is provided."""
    if not config.getoption("--run-llm-tests", default=False):
        skip_llm = pytest.mark.skip(
            reason="LLM integration tests skipped. Use --run-llm-tests to run."
        )
        for item in items:
            if "llm_integration" in item.keywords:
                item.add_marker(skip_llm)


@pytest.fixture
def test_config() -> Config:
    """Provide a test configuration."""
    return Config()


@pytest.fixture
def mock_config() -> Config:
    """Provide a test configuration with mock LLM provider."""
    config = Config()
    config.llm.provider = "mock"
    return config


@pytest.fixture
def sample_markdown() -> str:
    """Provide sample markdown content for testing."""
    return """
# Sample Technical Document

*A test document for the video explainer system.*

**This document explains how things work.**

---

## Introduction

Every time you do something, a process happens. This seems simple enough,
but the engineering required to make this fast is anything but.

Consider the numbers: a 7-billion parameter model stores its weights in
16-bit floating point (FP16), requiring exactly 14 gigabytes of memory.

## The Main Concept

### Quick Primer: The Basics

Before diving in, we need to understand the basics.

For each item, we compute three values:

- `Q = X · W_Q` (Query: "what am I looking for?")
- `K = X · W_K` (Key: "what do I contain?")
- `V = X · W_V` (Value: "what information do I provide?")

The computation is then:

```
Result = softmax(Q · K^T / √d) · V
```

The formula is $E = mc^2$ which shows the relationship.

![Diagram](images/diagram.gif)
*Animated walkthrough of the concept*

### Phase One: Setup

When you start, the system must first process your input. This is the
**setup phase**. All items are processed in parallel.

Setup is **compute-bound**. The GPU's cores are fully utilized.

### Phase Two: Execution

After setup comes the **execution phase**, which is fundamentally different.
We process items one at a time.

For each step, we must:

1. Load the weights from memory
2. Compute the new values
3. Store the results

Execution is **memory-bandwidth-bound**. The arithmetic intensity is low.

## Solution: Caching

The fix is simple: compute values once, then cache them in memory.

```python
def process_with_cache(input, cache):
    if input in cache:
        return cache[input]
    result = compute(input)
    cache[input] = result
    return result
```

This transforms O(n²) total work into O(n).

## Results

| Configuration | Throughput |
|---------------|------------|
| Naive | 40 items/s |
| With Cache | 600 items/s |
| Optimized | 3,500+ items/s |

From 40 to 3,500+ items per second. An **87× improvement**.

---

## Resources

- [GitHub Repository](https://github.com/example)
- [Documentation](https://docs.example.com)
"""


@pytest.fixture
def project_root() -> Path:
    """Return the project root directory."""
    return Path(__file__).parent.parent
