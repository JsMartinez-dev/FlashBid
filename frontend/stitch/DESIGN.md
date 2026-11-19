---
name: Editorial Vault
colors:
  surface: '#f9f9f6'
  surface-dim: '#dadad7'
  surface-bright: '#f9f9f6'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f4f4f1'
  surface-container: '#eeeeeb'
  surface-container-high: '#e8e8e5'
  surface-container-highest: '#e2e3e0'
  on-surface: '#1a1c1b'
  on-surface-variant: '#444748'
  inverse-surface: '#2f312f'
  inverse-on-surface: '#f1f1ee'
  outline: '#747878'
  outline-variant: '#c4c7c7'
  surface-tint: '#5f5e5e'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#1c1b1b'
  on-primary-container: '#858383'
  inverse-primary: '#c8c6c5'
  secondary: '#595f67'
  on-secondary: '#ffffff'
  secondary-container: '#dae0e9'
  on-secondary-container: '#5d636b'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#1a1c1a'
  on-tertiary-container: '#838482'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e5e2e1'
  primary-fixed-dim: '#c8c6c5'
  on-primary-fixed: '#1c1b1b'
  on-primary-fixed-variant: '#474746'
  secondary-fixed: '#dde3ec'
  secondary-fixed-dim: '#c1c7d0'
  on-secondary-fixed: '#161c23'
  on-secondary-fixed-variant: '#41474f'
  tertiary-fixed: '#e3e3e0'
  tertiary-fixed-dim: '#c6c7c4'
  on-tertiary-fixed: '#1a1c1a'
  on-tertiary-fixed-variant: '#454745'
  background: '#f9f9f6'
  on-background: '#1a1c1b'
  surface-variant: '#e2e3e0'
typography:
  display:
    fontFamily: Geist
    fontSize: 48px
    fontWeight: '600'
    lineHeight: 52px
    letterSpacing: -0.04em
  display-mobile:
    fontFamily: Geist
    fontSize: 36px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.03em
  headline-lg:
    fontFamily: Geist
    fontSize: 32px
    fontWeight: '500'
    lineHeight: 38px
    letterSpacing: -0.03em
  headline-lg-mobile:
    fontFamily: Geist
    fontSize: 26px
    fontWeight: '500'
    lineHeight: 32px
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Geist
    fontSize: 22px
    fontWeight: '500'
    lineHeight: 28px
    letterSpacing: -0.02em
  title-sm:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 22px
    letterSpacing: -0.01em
  body-lg:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 26px
    letterSpacing: -0.01em
  body-md:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: 0em
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.04em
  label-sm:
    fontFamily: Inter
    fontSize: 10px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.08em
spacing:
  gutter: 1.5rem
  gutter-sm: 1rem
  margin: 3rem
  margin-sm: 1.25rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style
The design system embodies a neo-brutalist minimal luxury aesthetic built on stark monochrome discipline, razor-sharp architectural geometry, and high-contrast precision. Designed for archiving, high-end editorial curation, and private collections, it conveys austere authority, archival longevity, and intellectual rigor.

The aesthetic rejects ornamental gradients and warm metallic hues, relying entirely on stark graphite black, cool platinum silver, and layered off-white tones. Micro-interactions are deliberate and crisp, evoking precision document handling and archival cataloging.

## Colors
The palette is strictly achromatic, eliminating all warm yellows, golds, and brass accents in favor of silver and graphite.

- **Primary (`#181818`)**: Graphite Black. Used for primary typography, authoritative actions, dense ink-style badges, and structural outlines.
- **Secondary (`#B8BEC7`)**: Platinum Silver. Used for refined technical accents, secondary borders, inactive tags, and subtle metadata labels.
- **Tertiary (`#E5E5E2`)**: Structural Cool Gray. Used for muted interactive states, disabled fills, and secondary card containers.
- **Neutral (`#F7F7F4`)**: Warm Off-White canvas base. Complemented by Pure White (`#FFFFFF`) for elevated paper cards, Soft Gray (`#E9E9E6`) for microscopic dividing lines, and Neutral Off-Base (`#F4F4F1`) for recessed inputs and panels.

## Typography
Typography reflects clinical typesetting and editorial mastery. `Geist` provides geometric clarity and sharp modernist contours for headlines, displays, and body copy. `Inter` is reserved for micro-labels, indexes, numbering, and functional tracking metadata.

Headlines employ tight tracking (`-0.02em` to `-0.04em`) to establish compact, headline-driven authority. Labels and numerical indexes use tracked uppercase configurations (`+0.04em` to `+0.08em`) to mimic archival catalog filing systems.

## Layout & Spacing
The layout adheres to a 12-column structured grid defined by strict alignment lines and hairline divisions. Margins and gutters expand gracefully across breakpoints:

- **Desktop (1024px+)**: 12-column grid with `3rem` canvas margins and `1.5rem` gutters. Structured panels and data sheets align along explicit borders.
- **Tablet (768px - 1023px)**: 8-column grid with `2rem` margins and `1rem` gutters.
- **Mobile (< 768px)**: 4-column fluid layout with `1.25rem` margins and `1rem` gutters.

Spacing enforces rhythmic multiples of 4px, prioritizing editorial airiness through deliberate whitespace contrasted against tightly packed, structured index tables.

## Elevation & Depth
Depth is created entirely through planar layering and crisp structural borders; drop shadows are strictly avoided.

- **Base Canvas**: Neutral Warm Off-White (`#F7F7F4`).
- **Elevated Surfaces**: Crisp Pure White (`#FFFFFF`) bound by single-pixel hairline dividers (`#E9E9E6`).
- **Recessed Areas & Wells**: Neutral Off-Base (`#F4F4F1`) and Cool Neutral (`#E5E5E2`) for data cards and input zones.
- **Divider Geometry**: 1px solid borders in Soft Gray (`#E9E9E6`) for resting surfaces, transitioning to Platinum Silver (`#B8BEC7`) on interactive focus or active division lines.

## Shapes
In line with neo-brutalist rigor, the shape system operates strictly at `roundedness: 0` (0px radius). All cards, tags, buttons, modals, and input controls feature sharp right angles. Architectural box models, square thumbnails, and hard grid intersections reinforce the physical nature of archival ledger cards.

## Components

### Buttons
- **Primary**: Solid Graphite Black (`#181818`) background, Pure White (`#FFFFFF`) typography, zero border radius, sharp 1px hairline border in `#181818`. On hover: Platinum Silver (`#B8BEC7`) background with `#181818` text.
- **Secondary**: Pure White (`#FFFFFF`) background, `#181818` text, and a crisp 1px `#181818` border. On hover: `#F4F4F1` surface fill.
- **Tertiary / Ghost**: Transparent fill, `#181818` text, underlined with a 1px `#B8BEC7` rule on hover.

### Chips & Badges
- Sharp, rectangular containers.
- **Archival Tag**: `#E5E5E2` background, 1px `#B8BEC7` border, uppercase `Inter` label in `#181818`.
- **Status Indicator**: 1px solid `#181818` outline, transparent fill, mono-spaced label.

### Lists & Tables
- Ledger-style presentation. Table headers set in uppercase `Inter` (`label-sm`) with a 1px solid `#181818` lower rule.
- Rows separated by 1px solid `#E9E9E6` horizontal rules. Row hover state transitions background subtly to `#FFFFFF`.

### Checkboxes & Radio Buttons
- **Checkbox**: 16x16px square, 0px border radius, 1px `#181818` border. Checked state features an inner filled `#181818` square with a 2px margin.
- **Radio Button**: 16x16px square (retaining sharp neo-brutalist syntax), 1px `#181818` border with a centered `#181818` inner square indicator.

### Input Fields
- Flat rectangular form boxes. Background in `#FFFFFF` or recessed `#F4F4F1`.
- Resting border: 1px `#E9E9E6`. Focus border: 1px solid `#181818`. No outline glows; clean geometric boundary only.
- Helper labels positioned strictly above input in `label-md`.

### Cards & Panels
- Framed in 1px `#E9E9E6` borders on `#FFFFFF` panels.
- Content headers are separated by full-width 1px hairline divider lines across the card canvas.

### Vault Indexer (Custom Component)
- Numerical catalog headers displaying classification stamps (e.g., `VOL. 01 / REF. 884`) paired with platinum silver (`#B8BEC7`) monospaced metadata bars.