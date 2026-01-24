# Evidence Pipeline Tests — Input/Output Paths & Artifacts

## Quick reference

| Test | Input | Output |
|------|--------|--------|
| **Mock/unit** | `{temp}/evidence/*.png` + manifest | `{temp}/evidence/manifest.json`, `curated/*.png` |
| **test_witness_capture_real_screenshot** | URL `https://example.com` | `{temp}/scene_1_fullpage.png`, `scene_1_viewport.png`, … |
| **test_full_pipeline_witness_to_curated** | URL `https://news.ycombinator.com` | `{temp}/evidence/*.png`, `manifest.json`, `curated/hn_001.png` |

`{temp}` = `tempfile.mkdtemp()` (e.g. `/var/folders/.../T/tmpXXXXXX/`). Use `--keep-artifacts` to skip cleanup and print the path.

---

## 1. Unit / Mock Tests (`-m "not slow"`)

**Root:** `{tempfile.mkdtemp()}` → e.g. `/var/folders/.../T/tmpXXXXXX/`

### Layout

```
{temp_dir}/
└── evidence/
    ├── manifest.json              # IN+OUT: created by fixture, updated by review/curate
    ├── test_001_element_padded.png # IN: from sample_manifest fixture
    ├── test_001_fullpage.png       # IN
    ├── test_002_element_padded.png # IN
    └── curated/                    # OUT: created by curate step
        ├── test_001.png
        └── test_002.png
```

### Per-Test

| Test | Input Paths | Output Paths |
|------|-------------|--------------|
| `test_manifest_load_save` | `evidence/` (empty manifest) | `evidence/manifest.json` |
| `test_review_with_mock` | `evidence/*.png` + manifest | `evidence/manifest.json` (review, best_variant) |
| `test_review_discovers_captures_from_files` | `evidence/article_001_*.png` only | `evidence/manifest.json` (discovered captures) |
| `test_curate_with_mock` | reviewed manifest + `evidence/*.png` | `evidence/curated/*.png`, manifest (curated) |
| `test_crop_image_function` | `evidence/source.png` | `evidence/cropped.png` |
| `test_review_then_curate_pipeline` | sample_manifest + PNGs | manifest + `evidence/curated/*.png` |
| `test_pipeline_clears_curated_when_rejected` | (same) | manifest only; curated cleared |

---

## 2. Witness Integration Tests (`@pytest.mark.slow`)

**Root:** `{tempfile.mkdtemp()}` — different dir per run, deleted in `finally` unless `--keep-artifacts`.

### `test_witness_capture_real_screenshot`

**Inputs:**
- **URL:** `https://example.com`
- **Description:** `"Example domain homepage"`
- **Output dir:** `{temp_dir}` (no `evidence/` subdir; Witness writes directly here)

**Outputs (Witness):**

```
{temp_dir}/
├── scene_1_fullpage.png    # always
├── scene_1_viewport.png    # often
├── scene_1_element_padded.png  # if element found
├── scene_1_element_tight.png   # if element found
└── scene_1_context.png     # sometimes
```

**Artifacts:** All under `{temp_dir}`. Removed after test unless `--keep-artifacts`.

---

### `test_full_pipeline_witness_to_curated`

**Inputs:**
- **URL:** `https://news.ycombinator.com`
- **Description:** `"Hacker News front page with tech headlines"`
- **Output dir:** `{temp_dir}/evidence/`

**Outputs by step:**

**Step 1 — Witness**
```
{temp_dir}/evidence/
├── scene_1_element_padded.png
├── scene_1_element_tight.png
├── scene_1_fullpage.png
├── scene_1_viewport.png
└── (sometimes scene_1_context.png)
```

**Step 2 — Reviewer**  
Reads `evidence/*.png` + manifest. Writes:

```
{temp_dir}/evidence/
└── manifest.json   # updated: review{}, best_variant, etc.
```

**Step 3 — Editor**  
Reads `evidence/{best_variant}.png`. Writes:

```
{temp_dir}/evidence/
├── manifest.json       # updated: curated{}, crop, dimensions
└── curated/
    └── hn_001.png      # cropped image
```

**Artifacts:** Everything under `{temp_dir}`. Removed after test unless `--keep-artifacts`.

---

## 3. Keeping Artifacts for Inspection

Run with `--keep-artifacts` to skip cleanup and print artifact root:

```bash
# Load env (Visual Truth Engine + main .env)
export $(cat visual-truth-engine/.env | xargs)
export $(cat .env | xargs)

# Unit/mock tests — artifacts under printed temp dir
pytest tests/test_evidence_pipeline.py -v -m "not slow" --keep-artifacts -s

# Full pipeline — Witness + Review + Curate
pytest tests/test_evidence_pipeline.py::TestWitnessIntegration::test_full_pipeline_witness_to_curated -v -s --keep-artifacts
```

The test will log something like:

```
Evidence pipeline artifacts kept at: /var/folders/.../T/tmpXXXXXX
  evidence/
  evidence/curated/
```

Inspect that path before the process exits.

---

## 4. Evidence Module Conventions (Non-Test)

| Path | Purpose |
|------|---------|
| `projects/{id}/evidence/` | Project evidence root |
| `projects/{id}/evidence/manifest.json` | Captures, review, curated metadata |
| `projects/{id}/evidence/*.png` | Raw screenshots (Witness or manually added) |
| `projects/{id}/evidence/curated/*.png` | Cropped, curated images |

CLI uses `projects_dir` (default `projects/`) and `project` id:

```bash
python -m src.cli evidence <project> review [--mock]
python -m src.cli evidence <project> curate [--mock]
python -m src.cli evidence <project> process [--mock]
```

So for `template-test`, all inputs/outputs live under `projects/template-test/evidence/`.
