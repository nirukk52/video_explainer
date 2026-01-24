# Templates Reference

This folder contains JSON schemas and examples for the 7 Shorts Factory templates.

## Template Overview

| Template | Description | Avatar | Use When |
|----------|-------------|--------|----------|
| `SplitProof` | Screenshot top, avatar bottom | Yes (bottom 40%) | Showing proof while explaining |
| `SplitVideo` | Video top, avatar bottom | Yes (bottom 40%) | Commenting on video footage |
| `TextOverProof` | Bold text over image | No | Key quotes, headlines |
| `FullAvatar` | Full screen talking head | Yes (full) | Opinion, transitions |
| `ProofOnly` | Screenshot fills frame | No | Document speaks for itself |
| `TextCard` | Text on gradient | No | Dramatic statements |
| `VideoCard` | Text top, rounded video center | No | Dramatic reveal with video |

## Files

```
templates/
├── schema.json              # JSON schema for validation
├── examples/
│   ├── SplitProof.json      # Example with comments
│   ├── TextOverProof.json
│   ├── FullAvatar.json
│   ├── ProofOnly.json
│   └── TextCard.json
└── screenshots/             # Visual reference (add after first render)
    ├── SplitProof.png
    ├── TextOverProof.png
    ├── FullAvatar.png
    ├── ProofOnly.png
    └── TextCard.png
```

## Usage

### For Agents

1. Read the example JSON for your chosen template
2. Replace values with your scene data
3. Validate against schema.json
4. Reference the screenshot to verify visual output

### For Validation

```python
import json
from jsonschema import validate

with open('templates/schema.json') as f:
    schema = json.load(f)

with open('projects/my-short/script/script.json') as f:
    script = json.load(f)

validate(instance=script, schema=schema)
```

## Template Selection Logic

```
Need to show evidence?
├── YES → Need avatar explaining?
│   ├── YES → SplitProof
│   └── NO → Key text to highlight?
│       ├── YES → TextOverProof
│       └── NO → ProofOnly
└── NO → Avatar talking?
    ├── YES → FullAvatar
    └── NO → TextCard
```

## Adding Screenshots

After rendering each template for the first time:

1. Take a screenshot of a representative frame
2. Save to `templates/screenshots/{TemplateName}.png`
3. Update the example JSON `_screenshot` field

This gives agents visual reference for template selection.
