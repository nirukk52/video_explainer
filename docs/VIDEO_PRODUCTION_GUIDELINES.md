# Video Production Guidelines

This document outlines the production standards for the video_explainer project. All scenes and components must adhere to these guidelines to ensure consistent, professional, and accessible video content.

---

## 1. Layout Principles

### Canvas Utilization
- **No wasted space** - Components should fill the 1920x1080 canvas appropriately
- **No overlapping elements** unless intentional for visual effect
- **Maintain consistent margins** - Typically 60-80px scaled from canvas edges

### Standard Layout Zones
```
┌─────────────────────────────────────────────────────────────┐
│ [Scene Indicator]                                           │
│  Top-left corner                                            │
│                                                             │
│                    ┌───────────────────┐                    │
│                    │                   │                    │
│                    │   MAIN CONTENT    │                    │
│                    │   (Center Area)   │                    │
│                    │                   │                    │
│                    └───────────────────┘                    │
│                                                             │
│                                          [Citations]        │
│                                          Bottom-right       │
└─────────────────────────────────────────────────────────────┘
```

### Key Positioning Rules
- **Scene indicator**: Always in top-left corner
- **Citations**: Always in bottom-right corner
- **Title**: Top area, below scene indicator
- **Main content**: Center (largest area, at least 60% of canvas)
- **Supporting info**: Bottom area, above citations

---

## 2. Citation Requirements

### Mandatory Citations
Every technical concept must cite its source paper. Citations appear **BOTH**:
1. In the narration (verbal acknowledgment)
2. As a visual overlay on screen

### Citation Format
```
"Paper Title - Authors, Venue Year"
```

**Examples:**
- `"ViT - Dosovitskiy et al., ICLR 2021"`
- `"Attention Is All You Need - Vaswani et al., NeurIPS 2017"`
- `"ResNet - He et al., CVPR 2016"`

### Visual Citation Behavior
- Citations should **fade in** when the concept is introduced
- Position in bottom-right corner with consistent padding
- Use `textDim` or `textMuted` color for non-intrusive appearance
- Font size: 14-16px scaled

### Narration Citation Style
Cite papers by mentioning author names naturally:
- "as introduced by Dosovitskiy and colleagues"
- "building on the work of Vaswani et al."
- "using the architecture proposed in the original Transformer paper"

---

## 3. Component Sizing Standards

### Typography Scale (in scaled pixels)
| Element | Size Range | Notes |
|---------|------------|-------|
| Title | 42-48px | Main scene headings |
| Subtitle | 20-26px | Section headers, key points |
| Body text | 18-22px | Explanations, descriptions |
| Labels | 14-18px | Diagram labels, annotations |
| Citations | 14-16px | Source references |

### Interactive/Visual Elements
- **Minimum touch target**: 40px scaled
- **Visualizations**: Should use at least 60% of available space
- **Icons/Indicators**: 24-32px for visibility

### Scaling Reference
Always use the `scale` function from styles to maintain proportional sizing across components:
```typescript
const fontSize = scale(24);  // Scales relative to canvas
```

---

## 4. Animation Best Practices

### Spring Animation Defaults
Use spring animations for natural, organic movement:
```typescript
spring({
  fps,
  frame,
  config: {
    damping: 12,
    stiffness: 100,
  },
})
```

### Timing Guidelines

| Animation Type | Duration (frames) | Notes |
|----------------|-------------------|-------|
| Fade in | 15-30 frames | Standard element appearance |
| Stagger delay | 10-20 frames | Between list items |
| Phase transitions | Proportional to durationInFrames | Calculate as percentage |

### Phase Timing Pattern
```typescript
const phase1End = durationInFrames * 0.3;
const phase2End = durationInFrames * 0.6;
const phase3End = durationInFrames * 0.9;
```

### Animation Principles
- **Proportional timing**: Phase durations should scale with total scene duration
- **Smooth easing**: Prefer spring or ease-out for entrances
- **Staggered reveals**: List items appear sequentially, not all at once
- **Avoid chaos**: No shaking or chaotic effects unless specifically requested
- **Anticipate bounds**: Ensure animated elements never leave canvas

---

## 5. Typography

### Font Family Usage
| Context | Font | Constant |
|---------|------|----------|
| Main text, headings, body | Neucha | `FONTS.handwritten` |
| Code, technical values | Monospace | `FONTS.mono` |

### Font Styling
```typescript
// Standard handwritten text
{
  fontFamily: FONTS.handwritten,
  fontWeight: 400,
  lineHeight: 1.5,
}

// Code/technical content
{
  fontFamily: FONTS.mono,
  fontWeight: 400,
}
```

### Typography Rules
- **Font weight**: Always 400 for handwritten fonts (heavier weights distort the style)
- **Line height**: 1.5 for body text (improves readability)
- **Letter spacing**: Default (no adjustment needed for Neucha)

---

## 6. Color Usage

### Color Palette (from styles.ts)
| Color | Use Case |
|-------|----------|
| `COLORS.primary` | Main headings, key elements, emphasis |
| `COLORS.secondary` | Supporting elements, contrasts |
| `COLORS.success` | Positive outcomes, solutions, checkmarks |
| `COLORS.error` | Problems, warnings, alerts |
| `COLORS.textDim` | Secondary text, less important info |
| `COLORS.textMuted` | Tertiary text, citations, captions |

### Color Application Guidelines
- **Consistency**: Use the same color for the same type of element across all scenes
- **Hierarchy**: Primary for most important, dim/muted for supporting
- **Meaning**: Success = good/solution, Error = problem/warning
- **Accessibility**: Ensure sufficient contrast against background

### Example Usage
```typescript
// Primary heading
color: COLORS.primary

// Supporting description
color: COLORS.textDim

// Error state
color: COLORS.error
```

---

## 7. Scene Structure

### Standard Scene Layout
Every scene should follow this structural hierarchy:

1. **Scene Indicator** (top-left)
   - Format: "Scene X" or numbered indicator
   - Small, unobtrusive but visible

2. **Title** (top area)
   - Main scene heading
   - 42-48px scaled

3. **Main Content** (center)
   - Largest area of the canvas
   - Primary visualizations and explanations
   - At least 60% of canvas space

4. **Supporting Info** (bottom)
   - Additional context, formulas, notes
   - Secondary to main content

5. **Citations** (bottom-right)
   - Source references
   - Fade in when concept introduced

### Overflow Prevention
- **Never let elements overflow the canvas**
- Test animations at all keyframes
- Add padding buffers for animated elements
- Clamp positions if necessary

---

## 8. Narration Guidelines

### Citation Integration
When referencing technical concepts, cite naturally:

**Do:**
- "as introduced by Dosovitskiy and colleagues in their 2021 paper"
- "building on the Transformer architecture from Vaswani et al."
- "using the Vision Transformer, or ViT, approach"

**Don't:**
- "according to ViT dash Dosovitskiy et al. comma ICLR 2021"
- Reading the citation format verbatim

### Technical Accuracy
- Keep technical terms accurate and consistent
- Spell out abbreviations on first use
- Use proper pronunciation for technical terms

### Pacing
- **Match narration to visual phases**: Speak about what's currently visible
- **Natural transitions**: Include verbal transitions between scenes
- **Breathing room**: Allow pauses for complex visualizations

### Transition Phrases
- "Now let's examine..."
- "Building on this concept..."
- "The key insight here is..."
- "As we can see..."

---

## 9. Common Issues to Avoid

### Layout Issues
| Issue | Prevention |
|-------|------------|
| Elements out of bounds | Test all animation keyframes |
| Overlapping components | Calculate exact positions; fade out old elements before showing new ones |
| Too much empty space | Make components LARGE (200-400px); use 60-70% of canvas |
| Text too small to read | Minimum 14px scaled for any text |
| Content spilling from boxes | Calculate content size first, add padding, use overflow:hidden |
| Broken arrows/connections | Ensure arrows connect fully from source to destination |

### Animation Issues
| Issue | Prevention |
|-------|------------|
| Jerky movement | Use spring animations with proper damping |
| Elements overlap at end | Calculate final positions carefully |
| Too fast/slow | Scale timing to durationInFrames |
| Chaotic motion | Keep animations purposeful and smooth |
| Incomplete sequences | Ensure loops complete for ALL items (e.g., all pixels flatten) |
| Narration/visual mismatch | Align phase timings with when concepts are mentioned in voiceover |

### Content Issues
| Issue | Prevention |
|-------|------------|
| Missing citations | Audit all technical claims |
| Inconsistent styling | Use constants from styles.ts |
| Audio mismatch | Verify scene IDs match audio files |
| Font weight issues | Always use 400 for handwritten fonts |
| Text placeholders for images | Use emoji, colored boxes, or visual representations |
| Brand names in examples | Use generic descriptions instead of company names |

---

## 10. Pre-render Checklist

Before rendering any scene, verify the following:

### Layout
- [ ] All elements within 1920x1080 bounds at all frames
- [ ] No unintentional overlapping elements
- [ ] Consistent margins (60-80px from edges)
- [ ] Scene indicator visible in top-left
- [ ] Main content uses adequate canvas space (60-70%)
- [ ] Components are LARGE, not tiny with wasted whitespace
- [ ] Content fits within container boxes (no spilling)
- [ ] Arrows/connections complete from source to destination

### Citations
- [ ] Citations present for all technical concepts
- [ ] Citations appear as visual overlay
- [ ] Citations mentioned in narration
- [ ] Citation format correct: "Title - Authors, Venue Year"

### Typography
- [ ] Font sizes readable (minimum 14px scaled)
- [ ] Correct font families (handwritten vs mono)
- [ ] Font weight 400 for handwritten fonts
- [ ] Line height 1.5 for body text

### Animation
- [ ] Animations smooth (spring config: damping 12, stiffness 100)
- [ ] Phase timings proportional to durationInFrames
- [ ] No elements leave canvas during animation
- [ ] Stagger delays appropriate (10-20 frames)
- [ ] Sequences complete for ALL items (no partial animations)
- [ ] Visuals sync with narration timing (show when mentioned)

### Content
- [ ] No text placeholders for images (use visuals/emoji instead)
- [ ] No brand names (use generic descriptions)
- [ ] Visual representations instead of text descriptions

### Style Consistency
- [ ] Color scheme consistent with COLORS constants
- [ ] Styling matches other scenes in the video
- [ ] Visual hierarchy clear (primary > secondary > muted)

### Audio
- [ ] Audio files exist for scene
- [ ] Audio filenames match scene IDs
- [ ] Narration pacing matches visual phases
- [ ] Transitions smooth between scenes

---

## Quick Reference

### Essential Constants
```typescript
// Canvas
const WIDTH = 1920;
const HEIGHT = 1080;

// Margins
const MARGIN = scale(60); // or scale(80) for more breathing room

// Spring config
const springConfig = { damping: 12, stiffness: 100 };

// Typography
const TITLE_SIZE = scale(45);
const BODY_SIZE = scale(20);
const LABEL_SIZE = scale(16);
```

### Common Patterns
```typescript
// Fade in animation
const opacity = interpolate(
  frame,
  [startFrame, startFrame + 20],
  [0, 1],
  { extrapolateRight: 'clamp' }
);

// Staggered list
items.map((item, index) => {
  const delay = index * 15; // 15 frame stagger
  // ... animation logic
});

// Phase-based timing
const phase1 = frame < durationInFrames * 0.3;
const phase2 = frame >= durationInFrames * 0.3 && frame < durationInFrames * 0.6;
```

---

*Last updated: January 2026*
*For the video_explainer Remotion project*
