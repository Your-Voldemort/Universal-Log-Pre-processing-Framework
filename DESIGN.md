---
name: ULPF Console
description: Lossless, air-gapped normalization of perimeter security logs into OCSF, for SOC analysts and compliance officers.
colors:
  # Light theme (the base). Canonical values are OKLCH; hex equivalents are in the prose below.
  accent: "oklch(0.47 0.085 208)"
  accent-hover: "oklch(0.41 0.08 208)"
  accent-ink: "oklch(0.45 0.085 208)"
  accent-soft: "oklch(0.945 0.022 208)"
  on-accent: "oklch(1 0 0)"
  ok: "oklch(0.49 0.1 155)"
  ok-soft: "oklch(0.95 0.035 155)"
  warn: "oklch(0.52 0.11 60)"
  warn-soft: "oklch(0.955 0.045 80)"
  bad: "oklch(0.51 0.165 27)"
  bad-soft: "oklch(0.95 0.03 25)"
  surface: "oklch(1 0 0)"
  canvas: "oklch(0.967 0.004 240)"
  raised: "oklch(0.953 0.005 240)"
  sunken: "oklch(0.976 0.004 240)"
  scrim: "oklch(0.2 0.012 245)"
  line: "oklch(0.905 0.007 240)"
  line-strong: "oklch(0.84 0.009 240)"
  control: "oklch(0.64 0.012 240)"
  ink: "oklch(0.24 0.014 245)"
  ink-2: "oklch(0.44 0.015 245)"
  ink-3: "oklch(0.52 0.013 245)"
  # Dark theme (OS preference or data-theme="dark"). on-accent and scrim are shared.
  accent-dark: "oklch(0.52 0.09 208)"
  accent-hover-dark: "oklch(0.47 0.085 208)"
  accent-ink-dark: "oklch(0.8 0.085 208)"
  accent-soft-dark: "oklch(0.28 0.04 215)"
  ok-dark: "oklch(0.79 0.12 155)"
  ok-soft-dark: "oklch(0.27 0.045 155)"
  warn-dark: "oklch(0.83 0.12 80)"
  warn-soft-dark: "oklch(0.29 0.05 70)"
  bad-dark: "oklch(0.76 0.13 28)"
  bad-soft-dark: "oklch(0.28 0.06 27)"
  surface-dark: "oklch(0.195 0.01 245)"
  canvas-dark: "oklch(0.165 0.009 245)"
  raised-dark: "oklch(0.24 0.012 245)"
  sunken-dark: "oklch(0.172 0.009 245)"
  line-dark: "oklch(0.285 0.012 245)"
  line-strong-dark: "oklch(0.36 0.013 245)"
  control-dark: "oklch(0.52 0.014 245)"
  ink-dark: "oklch(0.945 0.005 245)"
  ink-2-dark: "oklch(0.78 0.011 245)"
  ink-3-dark: "oklch(0.67 0.011 245)"
typography:
  headline:
    fontFamily: "Noto Sans, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: "1.75rem"
  figure:
    fontFamily: "Noto Sans, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: "1.75rem"
    fontFeature: "tnum"
  title:
    fontFamily: "Noto Sans, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 600
    lineHeight: "1.5rem"
  body:
    fontFamily: "Noto Sans, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: "1.375rem"
  data:
    fontFamily: "Noto Sans, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: "1.25rem"
  label:
    fontFamily: "Noto Sans, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: "1.125rem"
  mono:
    fontFamily: "JetBrains Mono, ui-monospace, SFMono-Regular, monospace"
    fontSize: "0.75rem"
    fontWeight: 400
    lineHeight: "1.25rem"
rounded:
  sm: "3px"
  default: "4px"
  md: "6px"
  full: "9999px"
spacing:
  "1": "4px"
  "1.5": "6px"
  "2": "8px"
  "2.5": "10px"
  "3": "12px"
  "4": "16px"
  "6": "24px"
  "8": "32px"
  "10": "40px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    typography: "{typography.data}"
    rounded: "{rounded.default}"
    padding: "0 12px"
    height: "32px"
  button-primary-hover:
    backgroundColor: "{colors.accent-hover}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.data}"
    rounded: "{rounded.default}"
    padding: "0 12px"
    height: "32px"
  button-secondary-hover:
    backgroundColor: "{colors.raised}"
  button-ghost:
    textColor: "{colors.ink-2}"
    typography: "{typography.data}"
    rounded: "{rounded.default}"
    padding: "0 12px"
    height: "32px"
  button-ghost-hover:
    backgroundColor: "{colors.raised}"
    textColor: "{colors.ink}"
  button-small:
    typography: "{typography.label}"
    padding: "0 10px"
    height: "28px"
  input:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.data}"
    rounded: "{rounded.default}"
    padding: "0 10px"
    height: "32px"
  nav-item:
    textColor: "{colors.ink-2}"
    typography: "{typography.data}"
    rounded: "{rounded.default}"
    padding: "0 8px"
    height: "32px"
  nav-item-active:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
  count-badge:
    backgroundColor: "{colors.warn-soft}"
    textColor: "{colors.warn}"
    typography: "{typography.label}"
    rounded: "{rounded.full}"
    padding: "0 6px"
  table-header:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink-2}"
    typography: "{typography.label}"
    padding: "8px 12px"
  table-cell:
    textColor: "{colors.ink}"
    typography: "{typography.data}"
    padding: "8px 12px"
  readout:
    backgroundColor: "{colors.sunken}"
    textColor: "{colors.ink}"
    typography: "{typography.mono}"
    rounded: "{rounded.default}"
    padding: "12px"
  callout-bad:
    backgroundColor: "{colors.bad-soft}"
    textColor: "{colors.ink-2}"
    typography: "{typography.data}"
    rounded: "{rounded.md}"
    padding: "10px 12px"
  panel:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.md}"
    padding: "16px"
---

# Design System: ULPF Console

## 1. Overview

**Creative North Star: "The Evidence Room"**

The ULPF console is where a SOC analyst on a night shift, or a compliance officer preparing for an audit, works with perimeter logs that have to hold up as evidence. The system behaves like a well-run evidence room: everything is labelled, filed in a fixed place, and linked to the original it came from. Nothing on screen is asserted without the record that proves it. A count links to its events, a verdict links to its hash, a drift alert shows the exact field that changed.

Density is a feature. Screens carry many rows and fields at 13px, and hierarchy comes from type weight, alignment, and spacing rather than boxes. Color is almost absent at rest: cool tinted neutrals and a single Petrol Blue accent for actions and selection. Semantic color (amber for drift, red for denial or tampering, green for verification) appears only where something needs or records a decision, and always with a shape and a text label. Motion is limited to state: 150 ms color transitions, a 200 ms panel slide, a spinner while waiting.

The system rejects, by name, every anti-reference in PRODUCT.md: Hollywood "hacker" consoles (neon green or cyan on black, glitch effects, scanlines, spinning globes with attack arcs); skeuomorphic props (the previous brass instrument-panel and wax-seal look, gunmetal textures, grid-paper backgrounds); generic SaaS dashboards (hero-metric tiles with gradient accents, identical card grids, decorative charts with no drill-down); consumer-app softness (oversized radii, pastel gradients, playful illustration); and anything that implies certification.

**Key Characteristics:**

- Two first-class themes, light and dark, following the OS setting with a manual switch.
- Restrained palette: tinted neutrals plus Petrol Blue on no more than 10% of a screen.
- One sans (Noto Sans) for the interface, one mono (JetBrains Mono) for evidence.
- Flat: depth from tonal layers and 1px hairlines, never drop shadows.
- Every status is a shape, a label, and a color, in that order of importance.
- Every time is UTC and says so.

## 2. Colors: The Evidence Room Palette

Cool, faintly blue-tinted neutrals carry the screen; Petrol Blue marks the one thing to do; three semantic hues speak only when a decision is pending or recorded.

Tokens live in `frontend/app/globals.css` as OKLCH channels and reach Tailwind as `oklch(var(--token) / <alpha-value>)`, so opacity modifiers work in both themes. `theme.colors` is replaced outright: the default Tailwind palette is not available. Values below are light / dark.

### Primary

- **Petrol Blue** (`accent`, #006874 / oklch(0.47 0.085 208); dark #007784 / oklch(0.52 0.09 208)): primary button fill and the one action per decision area. Hover darkens in both themes (#005661 light, #006874 dark) so white text stays above 4.5:1.
- **Petrol Ink** (`accent-ink`, #00626e / #78cdda): the accent as text and line. Links, the focus outline, the active nav icon.
- **Petrol Wash** (`accent-soft`, #ddf1f5 / #0d2e35): the selected table row, a newly seen field in a drift table, accent callouts.

### Secondary

Semantic state only, never decoration. Each has a strong value for marks and text and a soft wash for row and callout fills.

- **Verified Green** (`ok` #267147 / #77d199; `ok-soft` #ddf6e4 / #122d1d): chain intact, source matches its learned schema, event released after coercion.
- **Drift Amber** (`warn` #965719 / #f0be67; `warn-soft` #ffeecf / #3b260c): events held for review, IDS detections, pending counts in the navigation.
- **Denial Red** (`bad` #b1322d / #f98f82; `bad-soft` #ffe7e4 / #421c18): denied or dropped traffic, tampering, request errors, the API-unreachable banner.

### Neutral

- **Surface** (`surface`, #ffffff / #111519): the content plane. Tables, panels, inputs.
- **Canvas** (`canvas`, #f2f4f6 / #0b0f12): the second neutral layer. Sidebar, table header rows, segmented-control track.
- **Raised Mist** (`raised`, #edf0f2 / #1b2025): hover fills, skeleton blocks, event-ID chips, inline code.
- **Sunken Record** (`sunken`, #f5f7fa / #0d1014): evidence readouts. Raw logs, hashes, JSON, YAML.
- **Hairline** (`line`, #dce0e4 / #252b30) and **Hairline Strong** (`line-strong`, #c5cbd0 / #383e44): dividers and panel borders; the stronger one for step markers and the selected segment ring.
- **Control Edge** (`control`, #868d93 / #626a71): borders of inputs and secondary buttons, at 3:1 or better against surface and canvas.
- **Ink** (`ink`, #1a2026 / #eaedf0), **Ink Secondary** (`ink-2`, #4c545a / #b2b8be), **Ink Tertiary** (`ink-3`, #636a70 / #90969c): primary text, meta text and labels, placeholders and resting icons.
- **Scrim** (`scrim`, #12171b at 40%): behind the mobile navigation and the overlay event panel.

### Named Rules

**The One Voice Rule.** Petrol Blue covers no more than 10% of any screen: primary actions, current selection, focus, links. It is never a data bar, a section background, or decoration.

**The Calm-Until-It-Matters Rule.** Allowed traffic, healthy sources, and resolved items stay neutral. Amber, red, and green appear only on state that needs or records a decision.

**The Never-Color-Alone Rule.** Every status carries a text label and a shape: filled circle for ok, triangle for warn, square for bad, diamond for accent, hollow circle for neutral.

**The Measured Contrast Rule.** Contrast is measured, not eyeballed. Text is at least 4.5:1 in both themes (the lowest pair today is `ink-3` on `raised` in light, 4.79:1); control borders and focus rings at least 3:1. A new token ships only after it has been measured in both themes.

## 3. Typography

**Body Font:** Noto Sans (with system-ui, sans-serif)
**Label/Mono Font:** JetBrains Mono (with ui-monospace, SFMono-Regular, monospace)

Both load through `next/font/google`, which downloads them at build time and self-hosts them. Nothing is fetched at runtime, so air-gapped installs render identically.

**Character:** A neutral, wide-coverage sans that stays legible at 13px across a long shift (and has Devanagari companions if a bilingual interface is added), set against a mono with unambiguous 0/O and 1/l for IPs, event IDs, and hashes.

### Hierarchy

A fixed rem scale at roughly a 1.15 ratio. No fluid type.

- **Headline** (600, 1.25rem / 20px, line-height 1.75rem): the page title, one `h1` per screen.
- **Figure** (600, 1.25rem / 20px, tabular numerals): key values in the Overview stat strip.
- **Title** (600, 1rem / 16px, line-height 1.5rem): section `h2` headings such as "Sources" and "Hash chain".
- **Body** (400, 0.875rem / 14px, line-height 1.375rem): page descriptions and explanatory prose, capped at 72ch.
- **Data** (400 or 500, 0.8125rem / 13px, line-height 1.25rem): the default. Table cells, nav items, buttons, form values, field lists.
- **Label** (500, 0.75rem / 12px, line-height 1.125rem): table headers, form labels, captions, small buttons. Sentence case, no letter-spacing.
- **Mono** (400, 0.75rem / 12px, line-height 1.25rem): raw log lines, hashes, event IDs, IP:port pairs, timestamps, YAML and JSON.

### Named Rules

**The Sentence-Case Rule.** No uppercase tracked eyebrows anywhere. Navigation group labels, table headers, and captions are 12px sentence case.

**The Evidence-Is-Mono Rule.** Anything an analyst copies into a ticket or compares by eye (IDs, IPs, ports, hashes, timestamps, raw lines) is JetBrains Mono. Prose and labels never are.

**The Drawn Arrow Rule.** The self-hosted font subsets have no U+2192. Direction in the interface is the `Arrow` icon with a screen-reader "to", never a typed arrow glyph. Arrows inside backend-generated report Markdown are left as they are.

## 4. Elevation

Flat by default. There is no blurred `box-shadow` anywhere in the system. Depth comes from four tonal layers (canvas for chrome, surface for content, raised for hover and chips, sunken for evidence) plus 1px hairlines. The only shadow syntax in use is a 1px spread ring, `box-shadow: 0 0 0 1px oklch(var(--line))`, which acts as a border on the active nav item and the selected segment. Overlays (the mobile navigation, and the event panel below 1280px) separate from the page with a 40% scrim and a 1px border, not a drop shadow.

Stacking uses a named z-index scale and nothing else: `sticky` 20 (top bar), `scrim` 30, `drawer` 40.

### Named Rules

**The Flat-By-Default Rule.** Never add a blurred shadow to a panel, button, table, or drawer. If something must stand apart, move it to a different tonal layer or give it a hairline.

**The No-Nesting Rule.** A bordered container never holds another bordered container. Inside a panel, group with dividers and spacing.

## 5. Components

**Quiet and exact.** Hairline borders, 3 to 6px radii, 150ms color-only transitions. Nothing calls attention until it has to.

### Buttons

- **Shape:** 4px radius; 32px tall with 12px side padding (default) or 28px with 10px (small); 13px or 12px medium text; 6px gap to an icon.
- **Primary:** Petrol Blue fill, white text. Hover darkens to `accent-hover`. One primary per decision area.
- **Secondary:** surface fill, 1px Control Edge border, ink text. Hover fills `raised`.
- **Ghost:** no fill, `ink-2` text. Hover fills `raised` and darkens text to ink. Used for Cancel, Clear filters, Clear selection, Keep holding.
- **Loading:** a 14px ring spinner in `currentColor`; the button is disabled and `aria-busy`.
- **Disabled:** 50% opacity, no pointer events.
- **Consequential actions** (approving a parser) use an inline two-step confirm that explains the effect and focuses Cancel. Never a modal.

### Chips

- **Status:** an 8px shape, a 6px gap, then the label in ink. Shapes follow The Never-Color-Alone Rule.
- **Count badge:** full pill, `warn-soft` fill, `warn` text, 12px medium tabular numerals, with a screen-reader "awaiting review".
- **Event-ID chip:** 28px tall, 3px radius, `raised` fill, 12px mono, with a 24px remove button.

### Cards / Containers

- **Corner Style:** 6px for panels and table wrappers; 4px for readouts and inner tables.
- **Background:** surface; header rows on canvas.
- **Shadow Strategy:** none, see Elevation.
- **Border:** 1px `line`.
- **Internal Padding:** 16px for panels; 12px horizontal and 8px vertical for table cells; 10px by 12px for callouts.
- **Stat strip:** a grid with 1px gaps over the `line` color so the gaps draw the dividers; each cell is surface with 16px by 12px padding, a 12px `ink-2` label, a 20px semibold tabular value, and a 12px caption that truncates.
- **Callouts:** full 1px border in the tone at 25 to 35% opacity, the tone's soft fill, a 16px icon, title in ink medium, body in `ink-2`. Errors are `role="alert"`, ok and warn are `role="status"`. Never a side stripe.

### Inputs / Fields

- **Style:** 32px tall, 4px radius, 1px Control Edge border, surface fill, 13px text, 10px side padding. Hover darkens the border to `ink-3`; placeholders use `ink-3`.
- **Focus:** one global treatment for every interactive element: a 2px Petrol Ink outline at 2px offset on `:focus-visible`. The event-ID chip input shows it on its wrapper via `focus-within`.
- **Error / Disabled:** an inline 12px `bad` message below the field, linked with `aria-describedby`, and `aria-invalid` on the field. Disabled controls drop to 50% opacity.
- **Date and time:** native `datetime-local`, labelled "(UTC)". `color-scheme` follows the theme, so native pickers match.

### Tables

13px rows, 12px `ink-2` headers on canvas, hairline row dividers, hover at 60% `raised`, the selected row in Petrol Wash. The time column comes first, in mono with tabular numerals. Wide tables sit in a `relative overflow-x-auto` wrapper; `relative` matters, because without it screen-reader-only labels inside the table escape the scroller and widen the page on phones.

### Readouts

Evidence containers: `sunken` fill, 1px `line`, 4px radius, 12px JetBrains Mono on a 20px line, 12px padding, a capped height with internal scroll, and a 24px copy button beside the heading. The copy action falls back to `execCommand` because air-gapped installs are often served over plain http, where the Clipboard API is unavailable.

### Navigation

- **Sidebar:** 240px, `canvas`, grouped into Monitor, Review, and Evidence under 12px `ink-3` sentence-case labels. Items are 32px with a 4px radius and a 16px icon. Hover fills `raised`; the active item is surface with a 1px `line` ring, medium ink text, a Petrol Ink icon, and `aria-current="page"`. Review items carry count badges.
- **Top bar:** 56px, sticky, surface with a bottom hairline. Global event search, the last-updated time in UTC, and a chain-status link to Integrity.
- **Mobile (below 1024px):** the sidebar becomes an off-canvas drawer with a 200ms transform, a scrim, Escape to close, and `visibility: hidden` when closed so it leaves the tab order.
- **Theme switcher:** a three-icon segmented control (system, light, dark) at the foot of the sidebar. The choice is stored in localStorage and applied by an inline script before first paint.

### Event Detail Panel

The signature component: it turns a table row into its evidence. A field list (time, product, class, activity or finding, severity, disposition, endpoints, protocol), the raw log readout, a traceability list (SHA-256 hash, parser version, mapping confidence, drift review), disclosures for unmapped fields and the full OCSF JSON, and a "Draft incident report" action. At 1280px and wider it is a sticky 26rem second column beside the table; below that it is a full-height overlay up to 512px with a scrim, focus moved to Close on open and returned on exit. The open event lives in the URL (`?id=`), so any view can be shared.

## 6. Do's and Don'ts

### Do:

- **Do** link every count, status, and verdict to the record behind it (events, quarantine item, hash): evidence over assertion.
- **Do** keep Petrol Blue under 10% of a screen, and reserve amber, red, and green for state that needs or records a decision.
- **Do** pair every status color with a shape and a text label.
- **Do** show every time as UTC in `YYYY-MM-DD HH:MM:SS` and label it "(UTC)".
- **Do** format counts with Indian digit grouping (`en-IN`, 1,00,000).
- **Do** measure contrast for any new token in both themes: 4.5:1 for text, 3:1 for control borders and focus rings.
- **Do** give every screen a skeleton loading state, an empty state that teaches the next step, and an error state that shows the API's own message.
- **Do** use the exact sentence "ULPF provides technical controls and evidence that support applicable CERT-In/SEBI/NCIIPC requirements." wherever a regulator is named, with "CERT-In/SEBI/NCIIPC" kept on one line.
- **Do** confirm consequential actions inline with a two-step control.
- **Do** keep motion to state changes at 150 to 250ms with ease-out-quart, and honour `prefers-reduced-motion`.

### Don't:

- **Don't** build a Hollywood "hacker" console: neon green or cyan on black, glitch effects, scanlines, spinning globes with attack arcs.
- **Don't** bring back skeuomorphic props: the brass instrument-panel and wax-seal look, gunmetal textures, grid-paper backgrounds.
- **Don't** use generic SaaS dashboard furniture: hero-metric tiles with gradient accents, identical card grids, decorative charts with no drill-down.
- **Don't** add consumer-app softness: radii above 6px, pastel gradients, playful illustration.
- **Don't** imply certification: no "compliant" badges, no shield-with-checkmark compliance seals, never "ensures compliance".
- **Don't** add blurred box-shadows, glass or backdrop blur, or gradient text.
- **Don't** use a `border-left` or `border-right` wider than 1px as a colored stripe on callouts, rows, or panels.
- **Don't** put uppercase tracked eyebrows above sections or in table headers.
- **Don't** nest a bordered panel inside another bordered panel.
- **Don't** type "→" into interface copy; use the `Arrow` icon.
- **Don't** reach for the default Tailwind palette or arbitrary z-index values; the tokens and the sticky/scrim/drawer scale replace them on purpose.
