# Video Explainer System - Design Document

## Overview

A system that transforms technical resources (PDFs, research papers, documents, links) into high-quality, engaging explainer videos suitable for YouTube publication.

### Core Principles

1. **Quality over Speed**: Prioritize factual accuracy and engagement over rapid generation
2. **Human-in-the-Loop**: Maintain human review checkpoints until system reliability is proven
3. **Iterative Improvement**: Design for feedback incorporation and continuous refinement
4. **Budget Awareness**: Track and limit costs across all API/service usage
5. **Modular Architecture**: Each component should be independently testable and replaceable

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INPUT LAYER                                     │
│  PDFs, Research Papers, URLs, Documents, Images, Code Repositories          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CONTENT INGESTION                                    │
│  • Document Parsing (PDF, DOCX, HTML, Markdown)                             │
│  • Content Extraction (Text, Images, Equations, Code, Diagrams)             │
│  • Source Validation & Metadata Extraction                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CONTENT UNDERSTANDING                                   │
│  • Deep Analysis via LLM                                                     │
│  • Key Concept Extraction                                                    │
│  • Knowledge Graph Construction                                              │
│  • Complexity Assessment                                                     │
│  • Prerequisite Identification                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SCRIPT GENERATION                                      │
│  • Narrative Arc Design                                                      │
│  • Hook/Intro Creation                                                       │
│  • Concept Breakdown & Sequencing                                           │
│  • Analogy & Example Generation                                             │
│  • Visual Cue Annotations                                                   │
│  [HUMAN REVIEW CHECKPOINT #1]                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        STORYBOARDING                                         │
│  • Scene Decomposition                                                       │
│  • Visual Style Selection                                                    │
│  • Animation Requirements Specification                                      │
│  • Timing & Pacing Design                                                   │
│  [HUMAN REVIEW CHECKPOINT #2]                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ASSET GENERATION                                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │   Visuals    │  │    Audio     │  │  Animations  │  │   Graphics   │    │
│  │  Generation  │  │  Generation  │  │  Generation  │  │  Generation  │    │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘    │
│  [HUMAN REVIEW CHECKPOINT #3]                                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       VIDEO COMPOSITION                                      │
│  • Timeline Assembly                                                         │
│  • Audio-Visual Synchronization                                             │
│  • Transitions & Effects                                                    │
│  • Caption Generation                                                       │
│  [HUMAN REVIEW CHECKPOINT #4 - FINAL]                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           OUTPUT                                             │
│  Final Video (MP4) + Metadata + Thumbnails + Description                    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Deep Dive

### 1. Content Ingestion Module

**Purpose**: Transform diverse input formats into a unified, structured representation.

**Inputs Supported**:
| Format | Extraction Capabilities |
|--------|------------------------|
| PDF | Text, images, tables, equations (via OCR if needed) |
| Research Papers (arXiv, etc.) | Abstract, sections, citations, figures |
| Web URLs | Article content, embedded media, metadata |
| Markdown/Text | Structured text, code blocks |
| Code Repositories | README, key files, architecture |
| YouTube Videos | Transcript, key frames (for reference) |

**Key Challenges**:
- PDF parsing is notoriously difficult (especially for papers with complex layouts)
- Mathematical equations need special handling (LaTeX extraction)
- Diagrams need to be preserved with context

**Recommended Tools**:
- `PyMuPDF` / `pdfplumber` for PDF extraction
- `marker` (by VikParuchuri) for high-quality PDF-to-markdown
- `BeautifulSoup` / `trafilatura` for web scraping
- `Nougat` (Meta) for academic paper parsing with equations

**Output**: Structured document with:
```json
{
  "metadata": { "title", "authors", "date", "source_type" },
  "sections": [
    {
      "heading": "...",
      "content": "...",
      "images": [...],
      "equations": [...],
      "code_blocks": [...]
    }
  ],
  "references": [...],
  "key_figures": [...]
}
```

---

### 2. Content Understanding Module

**Purpose**: Deeply analyze the content to extract the "teachable essence."

**Key Operations**:

1. **Concept Extraction**: Identify the core concepts, their relationships, and hierarchy
2. **Complexity Mapping**: Assess which parts are complex and need more explanation
3. **Prerequisite Analysis**: What does the audience need to know beforehand?
4. **Key Insight Identification**: What are the "aha moments" in this content?
5. **Analogy Mining**: What real-world analogies could explain abstract concepts?

**LLM Strategy**:
- Use a powerful model (Claude Opus / GPT-4) for deep analysis
- Multi-pass analysis: first for structure, then for depth
- Generate a "concept map" that shows how ideas connect

**Output**: Knowledge representation including:
```json
{
  "core_thesis": "One sentence summary of what this content teaches",
  "key_concepts": [
    {
      "name": "...",
      "explanation": "...",
      "complexity": 1-10,
      "prerequisites": [...],
      "analogies": [...],
      "visual_potential": "high/medium/low"
    }
  ],
  "concept_graph": { "nodes": [...], "edges": [...] },
  "target_audience_assumptions": [...],
  "suggested_duration": "3-5 minutes"
}
```

---

### 3. Script Generation Module

**Purpose**: Create an engaging, accurate narrative script with visual annotations.

**Script Structure** (inspired by effective educational content):

1. **Hook** (0-15 seconds): Provocative question, surprising fact, or relatable problem
2. **Context Setting** (15-45 seconds): Why this matters, real-world relevance
3. **Core Explanation** (bulk of video): Concept-by-concept breakdown
4. **Key Insight/Climax**: The "aha moment"
5. **Implications/Applications**: What can you do with this knowledge?
6. **Call to Action**: Subscribe, explore further, etc.

**Script Format**:
```markdown
## SCENE 1: Hook
**VISUAL**: [Animation of data flowing through network]
**VO**: "What if I told you that the way ChatGPT understands language
        is fundamentally different from how you're reading this sentence?"
**DURATION**: 8 seconds
**NOTES**: Build intrigue, don't reveal the answer yet

## SCENE 2: Context
**VISUAL**: [Split screen: human brain vs neural network]
**VO**: "For decades, we tried to teach computers language the way
        we teach children—with rules and grammar..."
**DURATION**: 12 seconds
```

**Quality Criteria**:
- No jargon without explanation
- Every abstract concept has a concrete example or analogy
- Logical flow with clear transitions
- Appropriate pacing (not too dense)
- Factually accurate (verifiable against source)

**Human Review Checkpoint #1**:
- [ ] Script is factually accurate
- [ ] Flow is logical and engaging
- [ ] Complexity level is appropriate
- [ ] Visual cues are actionable
- [ ] Duration estimate is acceptable

---

### 4. Storyboarding Module

**Purpose**: Translate the script into a detailed visual plan.

**For Each Scene, Define**:
1. **Visual Type**: Animation, static graphic, code walkthrough, diagram, real footage
2. **Visual Description**: Detailed description of what should appear
3. **Motion/Animation**: How elements should move/appear
4. **Text Overlays**: Any on-screen text
5. **Timing**: Precise timing synced with voiceover

**Storyboard Format**:
```yaml
scene_id: 3
timestamp_start: "00:45"
timestamp_end: "01:12"
voiceover_text: "The transformer architecture revolutionized..."
visual:
  type: "animated_diagram"
  description: "Show transformer architecture building up layer by layer"
  elements:
    - id: "input_embedding"
      appear_at: 0.0
      animation: "fade_in_from_bottom"
    - id: "attention_block"
      appear_at: 2.5
      animation: "build_up"
      highlight: true
  style_reference: "3blue1brown_style"
  color_palette: ["#1e88e5", "#43a047", "#fb8c00"]
text_overlays:
  - text: "Self-Attention"
    position: "center"
    appear_at: 3.0
```

**Visual Style Guide**:
- Define a consistent visual language for the video
- Color palette, typography, animation style
- This ensures coherence across all scenes

**Human Review Checkpoint #2**:
- [ ] Visual descriptions are clear and producible
- [ ] Timing feels right when read aloud
- [ ] Visual style is consistent
- [ ] Complex concepts have adequate visual support

---

## Visual Style Guide: LLM Inference Series

This style guide defines the visual language for the first video series on LLM inference optimization.

### Color Palette

| Role | Color | Hex | Usage |
|------|-------|-----|-------|
| Background | Dark Slate | `#0f0f1a` | Primary background |
| Background Alt | Charcoal | `#1a1a2e` | Cards, containers |
| Compute/Data | Cyan | `#00d9ff` | Data flow, tokens, activations |
| Memory | Orange | `#ff6b35` | GPU memory, HBM, bandwidth |
| Optimization | Green | `#00ff88` | Improvements, solutions, gains |
| Warning/Problem | Red | `#ff4757` | Bottlenecks, problems |
| Neutral | Light Gray | `#e0e0e0` | Text, labels, borders |
| Accent | Purple | `#a855f7` | Highlights, emphasis |

### Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Main titles | Inter / SF Pro | 72px | Bold |
| Section headers | Inter / SF Pro | 48px | Semibold |
| Body text | Inter / SF Pro | 32px | Regular |
| Code / Numbers | JetBrains Mono | 28px | Regular |
| Labels | Inter / SF Pro | 24px | Medium |

### Visual Elements

**GPU/Hardware Representations**:
- Simplified rectangular blocks with rounded corners
- Subtle grid pattern to suggest silicon
- Glowing edges when "active"

**Data Flow**:
- Animated particles or pulses flowing along paths
- Cyan color for data, orange for memory transfers
- Bezier curves for connections, not straight lines

**Memory Blocks**:
- Grid of rectangular cells
- Fill animation to show utilization
- Color gradient from empty (dark) to full (orange)

**Tokens**:
- Rounded rectangles with text inside
- Subtle shadow for depth
- Animate in sequence during decode visualization

**Equations/Formulas**:
- LaTeX rendered, white on dark background
- Fade in term-by-term for complex equations
- Highlight active terms during explanation

### Animation Principles

1. **Timing**: Use easeInOutCubic for most transitions (smooth, professional)
2. **Duration**: 0.3-0.5s for element transitions, 1-2s for scene transitions
3. **Stagger**: When showing multiple elements, stagger by 0.1s for visual interest
4. **Focus**: Dim/blur non-essential elements when explaining specific concepts
5. **Build-up**: Complex diagrams should build piece by piece, not appear all at once

### Example Scene Specifications

**Prefill vs Decode Comparison**:
```
Left side: "Prefill" label
- Show all tokens processing in parallel (tokens light up simultaneously)
- GPU utilization bar fills to 100%
- Label: "Compute-bound"

Right side: "Decode" label
- Show tokens generating one-by-one (sequential light-up)
- GPU utilization bar low (~5%)
- Memory bandwidth bar high
- Label: "Memory-bound"
```

**KV Cache Visualization**:
```
- Show a vertical stack of K and V vectors
- Each decode step: new K,V pair animates into the cache
- Attention operation: Q vector "queries" the cache (draw attention lines)
- Highlight the O(n²) → O(n) improvement with counter
```

---

### 5. Asset Generation Module

This is the most complex module, with multiple sub-components:

#### 5.1 Visual Generation

**Types of Visuals Needed**:

| Visual Type | Generation Method | Tools/APIs |
|-------------|------------------|------------|
| Diagrams/Flowcharts | Programmatic generation | Motion Canvas, D3.js |
| Technical animations | Code-based animation | Motion Canvas |
| Conceptual illustrations | AI image generation | Midjourney, DALL-E 3, Flux |
| Code visualizations | Syntax highlighting + animation | Motion Canvas |
| Data visualizations | Programmatic | Motion Canvas, Chart.js |
| Icons/Simple graphics | Vector generation | SVG libraries, AI generation |

**Motion Canvas for Technical Animations**:
- TypeScript-based animation library (https://motioncanvas.io/)
- Modern, actively maintained, easier learning curve than alternatives
- Programmatic control over every visual element
- Native support for code highlighting, LaTeX, and complex transitions
- Outputs to video or image sequences
- Strong TypeScript typing for reliable code generation by LLMs

**AI Image Generation Strategy**:
- Use for conceptual illustrations where programmatic generation is impractical
- Always review for accuracy (AI can hallucinate visual details)
- Maintain consistent style through careful prompting

#### 5.2 Audio Generation

**Components**:
1. **Voiceover**: Text-to-Speech for narration
2. **Background Music**: Subtle, non-distracting ambient music
3. **Sound Effects**: Optional, for emphasis

**TTS Options** (ranked by quality):
1. **ElevenLabs**: Best quality, most natural, higher cost
2. **OpenAI TTS**: Good quality, reasonable cost
3. **Azure Neural TTS**: Good quality, enterprise-grade
4. **Coqui/Local TTS**: Lower quality, but free/cheap

**Voice Selection Criteria**:
- Clear, professional, engaging
- Appropriate pacing for educational content
- Consistent across videos (brand voice)

#### 5.3 Animation Generation

**Approach**:
Generate Motion Canvas TypeScript code programmatically via LLM, then render.

**Pipeline**:
```
Storyboard → LLM generates Motion Canvas code → TypeScript validation → Render → Review
```

**Why Motion Canvas**:
- **TypeScript-based**: Strong typing helps LLMs generate valid code
- **Modern tooling**: npm ecosystem, hot reload during development
- **Declarative animations**: Generator-based animation system is intuitive
- **Precise control**: Frame-accurate timing and appearance
- **Reproducible**: Code can be version controlled and iterated
- **Active community**: Good documentation and examples

**Motion Canvas Project Structure**:
```
animations/
├── src/
│   ├── scenes/
│   │   ├── intro.tsx
│   │   ├── prefill-decode.tsx
│   │   └── kv-cache.tsx
│   └── components/
│       ├── GPU.tsx
│       ├── DataFlow.tsx
│       └── MemoryBlock.tsx
├── package.json
└── motion-canvas.config.ts
```

**Human Review Checkpoint #3**:
- [ ] Visuals accurately represent concepts
- [ ] Audio is clear and well-paced
- [ ] Animations are smooth and meaningful
- [ ] Style is consistent throughout

---

### 6. Video Composition Module

**Purpose**: Assemble all assets into the final video.

**Key Operations**:
1. **Timeline Assembly**: Place all visual and audio elements on timeline
2. **Synchronization**: Align visuals precisely with voiceover
3. **Transitions**: Smooth transitions between scenes
4. **Effects**: Subtle effects (zoom, pan) for engagement
5. **Captions**: Generate accurate captions/subtitles

**Tools**:
- **FFmpeg**: Core video processing (composition, encoding)
- **MoviePy**: Python library for video editing
- **Remotion**: React-based video creation (if we go TypeScript)

**Output Formats**:
- Primary: MP4 (H.264) for YouTube
- Include: SRT/VTT captions
- Bonus: Thumbnail generation

**Human Review Checkpoint #4 (Final)**:
- [ ] Video plays smoothly
- [ ] Audio-visual sync is perfect
- [ ] No factual errors in final output
- [ ] Captions are accurate
- [ ] Ready for YouTube upload

---

## Budget Management

### Cost Tracking Architecture

```python
class BudgetManager:
    limits = {
        "llm_api": 50.00,        # Per video
        "tts_api": 10.00,        # Per video
        "image_generation": 20.00,  # Per video
        "total_per_video": 100.00
    }

    def check_budget(self, category, estimated_cost):
        # Prevent overspend
        pass

    def log_expense(self, category, actual_cost, description):
        # Track all API calls
        pass
```

### Cost Estimates Per Video (5-minute video)

| Component | Estimated Cost | Notes |
|-----------|---------------|-------|
| Content Understanding (LLM) | $2-5 | ~10K tokens analysis |
| Script Generation (LLM) | $3-8 | Multiple iterations |
| Storyboard Generation (LLM) | $2-5 | Detailed scene planning |
| Animation Code Generation (LLM) | $5-15 | Complex code generation |
| TTS (ElevenLabs) | $3-8 | ~1000 words |
| Image Generation | $5-15 | 5-10 images if needed |
| Compute (Rendering) | $2-5 | Video rendering |
| **Total** | **$22-61** | Per 5-min video |

### Cost Optimization Strategies

1. **Caching**: Cache LLM responses for similar queries
2. **Model Tiering**: Use cheaper models for simpler tasks
3. **Local Rendering**: Use local GPU for video rendering if available
4. **Batch Processing**: Batch similar API calls

---

## Human Review Interface

A simple web interface for reviewing outputs at each checkpoint.

**Features**:
- View generated content (script, storyboard, assets)
- Approve / Request Changes / Reject
- Inline editing for minor fixes
- Comment system for feedback
- Side-by-side comparison with source material

**Tech Stack**:
- Simple React/Next.js frontend
- Local file system for storage (initially)
- Could be CLI-based for v1

---

## Implementation Phases

### Phase 1: Foundation (MVP)
**Goal**: Generate an explainer video for "LLM Inference: Prefill vs Decode + KV Cache"

**Test Content**: `/Users/prajwal/Desktop/Learning/inference/website/post.md`
- Sections covered: "The Two Phases of Inference" through "KV Cache"
- Target duration: 3-4 minutes
- Self-contained concepts with clear visual potential

**Deliverables**:
1. Markdown ingestion with section extraction
2. Content analysis (key concepts: prefill, decode, attention, KV cache)
3. Script generation with visual cues
4. TTS voiceover generation (ElevenLabs or OpenAI)
5. Motion Canvas animations for:
   - Attention mechanism overview
   - Prefill vs Decode comparison
   - KV Cache building and reuse
6. Basic video assembly with FFmpeg
7. CLI-based human review at script stage

**Success Criteria**:
- Produces a watchable 3-4 minute video explaining prefill/decode/KV cache
- Factually accurate (verified by author)
- Visuals help explain the memory-bound vs compute-bound distinction
- Human can review and edit script before asset generation
- Total cost under $50 for this test video

### Phase 2: Full Article Coverage
**Goal**: Expand to cover the complete LLM inference article

**Deliverables**:
1. Additional sections: Continuous Batching, PagedAttention, Quantization
2. Reusable Motion Canvas component library (GPU, memory blocks, data flow)
3. More sophisticated storyboarding with scene transitions
4. Background music integration
5. Improved timing/pacing based on Phase 1 feedback

**Success Criteria**:
- Can produce 8-10 minute comprehensive video
- Component library enables faster iteration
- Consistent visual style across all sections

### Phase 3: Polish & Scale
**Goal**: Production-quality videos, longer content support

**Deliverables**:
1. Advanced animation capabilities
2. Multiple visual styles
3. Support for 10+ minute videos
4. YouTube metadata generation (title, description, tags, thumbnail)
5. Improved review interface
6. Cost optimization

**Success Criteria**:
- Videos are YouTube-ready without manual editing
- Can handle complex research papers
- Cost per video is predictable and within budget

### Phase 4: Intelligence & Automation
**Goal**: Reduce human intervention, improve quality

**Deliverables**:
1. Self-evaluation and quality scoring
2. Automatic fact-checking against sources
3. A/B testing framework for styles
4. Feedback loop from YouTube analytics
5. Batch processing capability

**Success Criteria**:
- Human intervention only needed for final approval
- Quality consistently high
- Can incorporate viewer feedback

---

## Technical Stack Recommendation

### Core Languages
- **Python**: Pipeline orchestration, LLM integration, content processing, CLI
- **TypeScript**: Animation generation via Remotion (React-based)

### Key Libraries & Tools

| Category | Tool | Purpose |
|----------|------|---------|
| Content Parsing | markdown parser | Markdown document extraction |
| LLM | Claude API, OpenAI API | Content understanding, script generation |
| TTS | ElevenLabs, Edge TTS | Voiceover generation with word timestamps |
| Animation | Remotion | React-based programmatic video rendering |
| Video | FFmpeg | Video composition and encoding |
| CLI | rich, argparse | Command-line interface |

### Project Structure

The system uses a **project-based organization** where each video project is self-contained:

```
video_explainer/
├── projects/                    # Self-contained video projects
│   └── llm-inference/           # Example: LLM Inference video
│       ├── config.json          # Project configuration
│       ├── narration/           # Scene narration scripts
│       │   └── narrations.json
│       ├── voiceover/           # Generated audio files
│       │   ├── manifest.json
│       │   └── *.mp3
│       ├── storyboard/          # Storyboard definitions
│       │   └── storyboard.json
│       ├── remotion/            # Video-specific React components
│       │   └── scenes/
│       └── output/              # Generated videos
│
├── src/                         # Core pipeline code
│   ├── cli/                     # CLI commands
│   ├── project/                 # Project loader module
│   ├── ingestion/               # Document parsing
│   ├── understanding/           # Content analysis (LLM)
│   ├── script/                  # Script generation
│   ├── audio/                   # TTS providers
│   ├── voiceover/               # Voiceover generation
│   ├── storyboard/              # Storyboard system
│   ├── animation/               # Animation rendering
│   ├── composition/             # Video assembly
│   ├── pipeline/                # End-to-end orchestration
│   ├── config.py                # Configuration management
│   └── models.py                # Pydantic data models
│
├── remotion/                    # Remotion project (React animations)
│   ├── src/
│   │   ├── components/          # Reusable animation components
│   │   ├── scenes/              # Scene compositions
│   │   └── types/               # TypeScript types
│   └── scripts/
│       └── render.mjs           # Headless rendering script
│
├── storyboards/                 # Storyboard schema
│   └── schema/
│       └── storyboard.schema.json
│
├── tests/                       # Test suite (241 tests)
├── config.yaml                  # Global configuration
└── pyproject.toml               # Python package configuration
```

### CLI Commands

The pipeline can be run independently via CLI:

```bash
# List all projects
python -m src.cli list

# Show project information
python -m src.cli info llm-inference

# Generate voiceovers (with mock TTS for testing)
python -m src.cli voiceover llm-inference --mock

# View storyboard
python -m src.cli storyboard llm-inference --view

# Render video
python -m src.cli render llm-inference

# Create a new project
python -m src.cli create my-new-video --title "My New Video"
```

---

## Risk Assessment & Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Factual errors in output | High | Medium | Multi-stage human review, source verification |
| Poor visual quality | Medium | Medium | Start simple, iterate based on feedback |
| High API costs | Medium | High | Budget limits, caching, model tiering |
| Complex papers too hard to explain | High | Medium | Start with simpler papers, build complexity |
| Motion Canvas code generation unreliable | Medium | Medium | TypeScript validation, manual fixes, build component library |
| TTS sounds robotic | Medium | Low | Use high-quality TTS (ElevenLabs) |
| Video too long/short | Low | Medium | Duration targets in script generation |

---

## Success Metrics

### Video Quality Metrics
- Factual accuracy: 100% (verified against source)
- Viewer retention (YouTube analytics): Target >50% average view duration
- Engagement: Likes/views ratio, comments quality

### System Metrics
- Time to produce video: Track and reduce over time
- Cost per video: Stay within budget
- Human intervention time: Reduce over phases
- Iteration cycles: Fewer rejections at review checkpoints

### Growth Metrics
- Videos published per month
- Subscriber growth
- Topics successfully covered

---

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Animation Library | Remotion (React) | Headless rendering, programmatic, actively maintained |
| Previous Choice | Motion Canvas | Moved away - no native headless rendering support |
| Project Organization | Self-contained projects | Each video project in `projects/` with all assets |
| Configuration | JSON files | Human readable, easy to edit, schema-validated |
| Pipeline Execution | CLI commands | Run stages independently, easier iteration |
| TTS Provider | ElevenLabs + Edge TTS | High quality with word timestamps, fallback option |
| Visual Style | Dark technical (see Style Guide) | Suits LLM inference topic, professional look |
| First Test Topic | LLM Inference (Prefill/Decode/KV Cache) | Author-written content, easy to verify, visual potential |
| Animation Approach | Storyboard-first | TTS timing drives visual sync, quality over automation |

## Open Questions

1. **Storyboard Automation**: When/how to introduce LLM-assisted storyboard generation?
2. **Component Reusability**: What patterns emerge from hand-crafted animations?
3. **Visual Metaphor Library**: How to catalog effective visual metaphors for reuse?

---

## Next Steps

1. **Set up project structure** and development environment (Python + Motion Canvas)
2. **Build content ingestion** for the test markdown file
3. **Implement script generation** with visual cue annotations
4. **Create first Motion Canvas animation** manually to validate the style
5. **Build the LLM → Motion Canvas code generation pipeline**
6. **Integrate TTS and video composition**
7. **Generate first complete video** and iterate

---

---

## Evolved Approach: Quality-First Animation (December 2024)

After initial implementation, we identified that **video quality is the critical success factor**. The templated, text-heavy approach doesn't produce engaging content. This section documents our evolved approach.

### The Problem with Automated Animation

The initial approach tried to map generic "visual cues" to generic components (title cards, text reveals). This produces:
- Too much text on screen
- Generic animations that don't explain concepts
- No visual storytelling—just information display

### The Solution: Storyboard-First, Hand-Crafted Animations

**Full Pipeline:**

```
Document
    ↓
┌─────────────────────────────────────────────────────────────────┐
│  Content Understanding → Script Generation                      │
│  (existing modules)                                             │
└─────────────────────────────────────────────────────────────────┘
    ↓
Script (narrative + voiceover text per scene)
    │
    ├──────────────────────────────────┐
    ↓                                  ↓
┌─────────────────────┐    ┌─────────────────────────────────────┐
│  TTS Generation     │    │  Storyboard Generator               │
│  - Audio files      │    │  - Takes script + audio timing      │
│  - Word timestamps  │───→│  - Outputs structured JSON          │
│  (ElevenLabs)       │    │  - Hand-crafted initially           │
└─────────────────────┘    │  - LLM-assisted eventually          │
                           └─────────────────────────────────────┘
                                       ↓
                           Storyboard (JSON)
                           - Beat-by-beat timing
                           - Component references
                           - Sync points to audio
                                       ↓
                           ┌─────────────────────────────────────┐
                           │  Scene Assembler                    │
                           │  - Resolves component references    │
                           │  - Generates Remotion scenes        │
                           └─────────────────────────────────────┘
                                       ↓
                           Animation (Remotion)
                                       ↓
                           ┌─────────────────────────────────────┐
                           │  Composer                           │
                           │  - Combines audio + video           │
                           │  - Final encoding                   │
                           └─────────────────────────────────────┘
                                       ↓
                           Final Video (MP4)
```

**Key Insight**: TTS must happen BEFORE storyboard generation because we need audio timing (word-level timestamps) to sync visuals precisely to narration.

**Key Principles:**

1. **Storyboard before animation**: Every scene needs frame-by-frame visual planning synchronized to voiceover. No more vague "visual cues."

2. **Hand-craft animations for each topic**: Each concept needs custom-designed visuals that actually demonstrate the concept, not generic templates.

3. **Quality over automation**: It's okay to be slow. The focus is producing genuinely good explainer content.

4. **Build reusable primitives**: As we hand-craft animations, identify patterns that can become reusable components.

5. **Eventually LLM-assisted**: Once we understand what good storyboards look like, we can train/prompt LLMs to generate them.

### Storyboard Format

Storyboards are structured JSON files that define exactly what happens and when. See `/storyboards/schema/` for the formal schema and `/storyboards/examples/` for references.

**Schema location**: `storyboards/schema/storyboard.schema.json`

**Key elements**:
- **Beats**: Time-based segments with start/end times
- **Elements**: Component instances with props and animations
- **Sync points**: Audio triggers that fire visual actions
- **Transitions**: How elements enter/exit

**Example structure**:
```json
{
  "id": "prefill_vs_decode",
  "title": "Prefill vs Decode",
  "duration_seconds": 60,
  "audio": {
    "file": "prefill_vs_decode.mp3",
    "duration_seconds": 58.5
  },
  "beats": [
    {
      "id": "setup",
      "start_seconds": 0,
      "end_seconds": 5,
      "voiceover": "When you send a prompt to an LLM, two very different things happen.",
      "elements": [...]
    }
  ]
}
```

See `/storyboards/prefill_vs_decode.md` for the human-readable design document.
See `/storyboards/examples/prefill_vs_decode.json` for the machine-readable storyboard.

### Animation Component Library

Components are reusable Remotion React components referenced by storyboards. Each component has a defined interface (props) that the storyboard can configure.

**Component Registry** (`remotion/src/components/registry.ts`):
```typescript
const componentRegistry = {
  // Core components (reusable across topics)
  "prompt_input": PromptInput,
  "text_reveal": TextReveal,
  "comparison_layout": ComparisonLayout,

  // LLM Inference components
  "token": Token,
  "token_row": TokenRow,
  "gpu_gauge": GPUGauge,

  // Future topics will add more...
};
```

**Current Components** (LLM Inference):

| Component | Props | Description |
|-----------|-------|-------------|
| `token` | `text`, `isActive`, `activateAt` | Single token with glow animation |
| `token_row` | `tokens[]`, `mode: "prefill"\|"decode"`, `activateAt` | Row with parallel or sequential activation |
| `gpu_gauge` | `utilization`, `status: "compute"\|"memory"`, `animateAt` | Utilization bar with status label |

**Adding New Components**:
1. Create component in `remotion/src/components/`
2. Define clear props interface
3. Add to component registry
4. Document in this section

Components should be:
- **Configurable**: Props control appearance and behavior
- **Animatable**: Accept timing props (`activateAt`, `duration`)
- **Composable**: Work well with other components

### What Success Looks Like

A successful scene should:
1. **Explain through visuals**, not text labels
2. **Create "aha moments"** where the viewer understands *why*
3. **Be watchable without sound** (visuals carry meaning)
4. **Feel intentional** - every animation has a purpose

---

## Feedback System (December 2024)

### Overview

The feedback system enables iterative video improvement through natural language feedback. Users can describe changes they want, and the system uses Claude Code CLI in headless mode to analyze the feedback and apply intelligent changes to project files.

### Architecture

```
User Feedback (natural language)
         │
         ▼
┌─────────────────────────┐
│   Feedback Processor    │
│  ┌───────────────────┐  │
│  │ ClaudeCodeLLM     │  │
│  │ Provider          │  │
│  └───────────────────┘  │
│         │               │
│         ▼               │
│  ┌───────────────────┐  │
│  │ Analyze Feedback  │  │──► Identify scope, affected scenes
│  └───────────────────┘  │
│         │               │
│         ▼               │
│  ┌───────────────────┐  │
│  │ Create Preview    │  │──► Git branch: feedback/<id>
│  │ Branch            │  │
│  └───────────────────┘  │
│         │               │
│         ▼               │
│  ┌───────────────────┐  │
│  │ Apply Changes     │  │──► Modify storyboard, narrations
│  └───────────────────┘  │
│         │               │
└─────────┼───────────────┘
          ▼
┌─────────────────────────┐
│   Feedback Store        │
│   (feedback.json)       │
└─────────────────────────┘
```

### Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `ClaudeCodeLLMProvider` | `src/understanding/llm_provider.py` | Execute Claude Code CLI for LLM operations |
| `FeedbackItem` | `src/feedback/models.py` | Data model for feedback with status tracking |
| `FeedbackHistory` | `src/feedback/models.py` | Collection of feedback items for a project |
| `FeedbackStore` | `src/feedback/store.py` | JSON persistence for feedback history |
| `FeedbackProcessor` | `src/feedback/processor.py` | Main processing logic |

### CLI Commands

```bash
# Add and process feedback
python -m src.cli feedback <project> add "<feedback_text>"

# Analyze without applying (dry run)
python -m src.cli feedback <project> add "<text>" --dry-run

# Skip preview branch creation
python -m src.cli feedback <project> add "<text>" --no-branch

# List all feedback
python -m src.cli feedback <project> list

# Show feedback details
python -m src.cli feedback <project> show <feedback_id>
```

### Preview Branch Workflow

1. User runs `feedback add "<text>"`
2. System creates branch `feedback/<feedback_id>`
3. Claude Code makes changes on that branch
4. User reviews with `git diff main`
5. User merges with `git checkout main && git merge feedback/<id>` or discards

### Feedback States

| State | Description |
|-------|-------------|
| `pending` | Feedback recorded, not yet processed |
| `processing` | Currently being analyzed/applied |
| `applied` | Successfully applied changes |
| `rejected` | User rejected the changes |
| `failed` | Processing failed (see error_message) |

### Data Storage

Feedback is stored in `projects/<project>/feedback/feedback.json`:

```json
{
  "project_id": "llm-inference",
  "items": [
    {
      "id": "fb_0001_1234567890",
      "timestamp": "2024-12-29T10:30:00",
      "feedback_text": "Make the text larger in scene 1",
      "status": "applied",
      "scope": "scene",
      "affected_scenes": ["scene_01"],
      "interpretation": "User wants larger font size",
      "files_modified": ["storyboard/storyboard.json"],
      "preview_branch": "feedback/fb_0001_1234567890"
    }
  ]
}
```

---

---

## Sound Design System (December 2024)

### Overview

The sound design system adds professional audio polish through frame-accurate SFX that sync with animation events. SFX cues are defined in storyboard.json and rendered directly by Remotion.

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Sound Design Pipeline                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Storyboard.json ──────────────────────► Remotion               │
│  (scenes + sfx_cues)                     (renders video with    │
│       │                                   SFX at exact frames)  │
│       │                                                          │
│       ▼                                                          │
│  SFX Library ──────────────────────────► projects/<id>/sfx/     │
│  (10 procedural sounds)                  (WAV files)            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Key Principle: Animation-Driven SFX

Sounds are tied to **visual events**, not narration content:

| Animation Event | Sound | Volume |
|----------------|-------|--------|
| Element appears | `ui_pop` | 0.08 |
| Text/typing | `text_tick` | 0.06 |
| Block locks in place | `lock_click` | 0.1 |
| Data flowing | `data_flow` | 0.08 |
| Fast counter | `counter_sweep` | 0.12 |
| Big reveal (87x) | `reveal_hit` | 0.15 |
| Problem state | `warning_tone` | 0.1 |
| Solution found | `success_tone` | 0.1 |
| Phase transition | `transition_whoosh` | 0.1 |
| Cache operation | `cache_click` | 0.1 |

### SFX Cues in Storyboard

SFX cues are defined per scene in `storyboard.json`:

```json
{
  "id": "scene1_hook",
  "type": "llm-inference/hook",
  "title": "The Speed Problem",
  "audio_file": "scene1_hook.mp3",
  "audio_duration_seconds": 18.52,
  "sfx_cues": [
    {"sound": "ui_pop", "frame": 15, "volume": 0.08},
    {"sound": "text_tick", "frame": 30, "volume": 0.06},
    {"sound": "transition_whoosh", "frame": 270, "volume": 0.1},
    {"sound": "counter_sweep", "frame": 330, "volume": 0.12},
    {"sound": "reveal_hit", "frame": 390, "volume": 0.15}
  ]
}
```

### CLI Commands

```bash
# List available sounds
python -m src.cli sound <project> library --list

# Generate SFX files to project's sfx/ directory
python -m src.cli sound <project> library --generate
```

### Project Structure

```
projects/<project>/
├── sfx/                   # SFX files (used by Remotion)
│   ├── ui_pop.wav
│   ├── lock_click.wav
│   └── ...
├── storyboard/
│   └── storyboard.json    # Includes sfx_cues per scene
└── voiceover/
    └── ...
```

### Workflow

1. **Analyze animations** to identify visual events
2. **Add sfx_cues** to storyboard.json with frame-accurate timing
3. **Generate SFX** using CLI: `sound library --generate`
4. **Render video** - Remotion plays SFX at specified frames

---

*Document Version: 1.6*
*Last Updated: December 2024*
*Current Status: 402+ tests passing, frame-accurate sound design*
