---
name: sil-brand-web
description: This skill should be used when designing or building SIL web applications, websites, or UI components. Use when the user asks about "SIL brand colors", "SIL fonts", "SIL typography", "SIL design guidelines", "brand-compliant UI", or when creating any SIL-branded web interface. Covers colors, typography, logo usage, and design principles from the SIL Brand Manual v1.1.
---

# SIL Brand Guidelines for Web Design

Reference for applying SIL's visual brand to web applications and UI design. Source: SIL Brand Manual v1.1 (Mar 2024).

## Colors

Use RGB or HEX values for web. Each accent color has a standard and dark variant for hover states, borders, and depth.

### Primary Palette (Blues)

| Name             | HEX       | RGB            | Usage                                      |
|------------------|-----------|----------------|--------------------------------------------|
| SIL Blue         | `#005CB9` | 0, 92, 185     | Primary brand color; buttons, links, CTAs  |
| SIL Dark Blue    | `#034D8A` | 3, 77, 138     | Hover states, dark variant of SIL Blue     |
| SIL Bright Blue  | `#00A7E1` | 0, 167, 225    | Logo glyph box, accents, highlights        |
| SIL Teal         | `#008AAF` | 0, 138, 175    | Dark variant of Bright Blue                |

The logo uses:
- SIL box background: **SIL Blue** (`#005CB9`), white "SIL" text
- Glyph box background: **SIL Bright Blue** (`#00A7E1`) at 100%
- Glyph itself: SIL Bright Blue at 75% opacity

### Accent Palette

Each accent color has a lighter (primary) and darker variant. Use primaries for UI elements and darks for hover/active states.

| Name           | Primary HEX | Primary RGB      | Dark HEX  | Dark RGB       |
|----------------|-------------|------------------|-----------|----------------|
| Yellow         | `#FFB71B`   | 255, 183, 27     | `#D99408` | 217, 148, 8    |
| Green          | `#509E2F`   | 80, 158, 47      | `#38751C` | 56, 117, 28    |
| Orange         | `#FF6B00`   | 255, 107, 0      | `#C24F00` | 194, 79, 0     |
| Red            | `#D52227`   | 213, 34, 39      | `#A6121F` | 166, 18, 31    |
| Purple         | `#93358D`   | 147, 53, 141     | `#6B2169` | 107, 33, 105   |

### Color Use Principles

- **3 Color Rule**: Use no more than 3 colors in a single design or component.
- **Balanced Contrast**: Pair light and dark values for accessible, readable contrast.
- **Complementary Colors**: Choose colors that work together; don't combine all accents at once.
- **Consistency**: Use the same color roles throughout a design (e.g., always use SIL Blue for primary CTAs).

### CSS Custom Properties (recommended setup)

```css
:root {
  /* Primary Blues */
  --sil-blue:         #005CB9;
  --sil-blue-dark:    #034D8A;
  --sil-bright-blue:  #00A7E1;
  --sil-teal:         #008AAF;

  /* Accents */
  --sil-yellow:       #FFB71B;
  --sil-yellow-dark:  #D99408;
  --sil-green:        #509E2F;
  --sil-green-dark:   #38751C;
  --sil-orange:       #FF6B00;
  --sil-orange-dark:  #C24F00;
  --sil-red:          #D52227;
  --sil-red-dark:     #A6121F;
  --sil-purple:       #93358D;
  --sil-purple-dark:  #6B2169;
}
```

---

## Typography

All three fonts are free and available at [fonts.google.com](https://fonts.google.com).

### The Three SIL Fonts

| Font           | Classification | Primary Use                          | Google Fonts Name  |
|----------------|---------------|--------------------------------------|--------------------|
| **Playfair**   | Serif         | Headlines, quotes, hero text         | Playfair Display   |
| **Lora**       | Serif         | Body copy, captions, smaller text    | Lora               |
| **Source Sans 3** | Sans-serif | Subheadings, labels, alternative body | Source Sans 3     |

> Source Sans 3 was formerly called "Source Sans Pro." Both names may appear in older materials.
> Sub-brand logo descriptors use **Source Sans Pro Semibold** specifically.

### Type Hierarchy

| Role        | Font                  | Weight    | Style Notes                              |
|-------------|-----------------------|-----------|------------------------------------------|
| H1 / Header | Playfair              | Medium    |                                          |
| Subhead     | Source Sans 3         | Semibold  | ALL CAPS, letter-spacing: 0.14em (140)   |
| Body Copy   | Lora                  | Regular   |                                          |
| Quotes      | Playfair              | Regular   | Can use bolder weights if situation warrants |
| Labels/Caps | Source Sans 3         | Regular   | ALL CAPS + tracking                      |

### Available Weights

**Playfair**: Regular, Italic, Medium, Medium Italic, Semibold, Semibold Italic, Bold, Bold Italic, Black, Black Italic

**Lora**: Regular, Italic, Medium, Medium Italic, Semibold, Semibold Italic, Bold, Bold Italic

**Source Sans 3**: Extra Light, Extra Light Italic, Light, Light Italic, Regular, Italic, Semibold, Semibold Italic, Bold, Bold Italic, Black, Black Italic

### Google Fonts Import

```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500;1,600;1,700&family=Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;0,800;0,900;1,400;1,500;1,600;1,700;1,800;1,900&family=Source+Sans+3:ital,wght@0,200;0,300;0,400;0,600;0,700;0,900;1,200;1,300;1,400;1,600;1,700;1,900&display=swap" rel="stylesheet">
```

```css
:root {
  --font-heading: 'Playfair Display', Georgia, serif;
  --font-body:    'Lora', Georgia, serif;
  --font-ui:      'Source Sans 3', system-ui, sans-serif;
}

h1, h2 { font-family: var(--font-heading); font-weight: 500; }
h3, h4, h5, h6, .subhead { font-family: var(--font-ui); font-weight: 600; text-transform: uppercase; letter-spacing: 0.14em; }
body, p, li { font-family: var(--font-body); font-weight: 400; }
blockquote { font-family: var(--font-heading); font-weight: 400; }
```

---

## Logo

When displaying the SIL logo in web contexts:

- **Minimum width**: 0.75 inches (≈72px at 96dpi) for full-color; 1 inch (≈96px) for monochrome
- **Clear space**: Maintain padding equal to at least 1/4 of the logo's box height on all sides
- **SIL box**: SIL Blue (`#005CB9`) background, white "SIL" text — never alter these colors
- **Glyph box**: SIL Bright Blue (`#00A7E1`) background with glyph at 75% opacity
- Use the full logo (glyph box + SIL box) — never the SIL box alone
- On dark or colored backgrounds, use the monochrome (white) logo version
- Do not stretch, rotate, recolor, or add effects

### Sub-brand Logos

Descriptors (e.g., "SIL Language Technology") use **Source Sans Pro Semibold**, sentence case, with the first letter of each word capitalized.

---

## Design Elements
Three brand-approved decorative elements for backgrounds and graphics:
- **Glyph bars** — horizontal strips containing SIL glyphs
- **Topographical backgrounds** — layered line patterns
- **Glyph backgrounds** — large, semi-transparent glyph forms as texture

These reinforce the SIL brand identity without adding semantic meaning.
