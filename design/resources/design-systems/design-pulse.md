# PulsePoint
*Clinical, precise, data-driven — every pixel accountable to patient safety.*

## Overview

PulsePoint is a dark-mode design system engineered for medical device dashboards and vital-sign monitoring interfaces. It treats screen real estate as a scarce clinical resource, packing dense data into compact, scannable layouts. Alert hierarchy is foundational: critical red cuts through the dark canvas instantly, while steel and navy tones recede to let vital numbers lead. Glow-based elevation reinforces status severity without adding visual clutter.

---

## Colors

- **Primary Navy** (#1E3A5F): Primary containers, navigation, headers
- **Secondary Red** (#E63946): Alerts, critical vitals, destructive actions
- **Tertiary Steel** (#8D99AE): Secondary text, inactive elements, borders
- **Neutral Slate** (#64748B): Muted labels, dividers, disabled states
- **Background** (#0F172A): Page background (dark base)
- **Surface** (#1E293B): Cards, panels, modals
- **Success** (#22C55E): Normal vitals, stable indicators
- **Warning** (#F59E0B): Caution alerts, borderline readings
- **Error** (#E63946): Critical alerts, dangerous vitals
- **Info** (#3B82F6): Informational, connectivity status

## Typography

- **Headline Font**: Red Hat Display
- **Body Font**: Inter
- **Mono Font**: JetBrains Mono

- **Display**: Red Hat Display 36px bold, 1.15 line height, 0.02em tracking
- **Headline**: Red Hat Display 28px bold, 1.2 line height, 0.01em tracking
- **Subhead**: Red Hat Display 20px semibold, 1.3 line height
- **Body Large**: Inter 16px regular, 1.5 line height
- **Body**: Inter 14px regular, 1.5 line height
- **Body Small**: Inter 13px regular, 1.45 line height, 0.01em tracking
- **Caption**: Inter 11px medium, 1.35 line height, 0.02em tracking
- **Overline**: Inter 10px bold, 1.3 line height, 0.1em tracking
- **Code**: JetBrains Mono 13px regular, 1.5 line height

---

## Spacing

- **Base unit:** 4px (compact, data-dense layouts)
- **Scale:** 2 / 4 / 8 / 12 / 16 / 20 / 24 / 32 / 48
- **Component padding:** 12px horizontal, 8px vertical (buttons/inputs)
- **Section spacing:** 24px between dashboard panels, 12px between related widgets

## Border Radius

- **None** (0px): Data tables, full-bleed panels
- **Small** (2px): Badges, micro-indicators
- **Medium** (4px): Cards, inputs, buttons
- **Large** (6px): Modals, dialogs
- **XL** (8px): Feature panels, hero widgets
- **Full** (9999px): Status dots, avatar circles

## Elevation

**Philosophy:** Dark-mode glow effects. Blue glow for informational elevation, red glow for alert-level severity. Shadows emit light rather than cast darkness.
- **Subtle**: 1px offset, 3px blur, #000000 at 40%, 8px glow #1E3A5F at 15%
- **Medium**: 4px offset, 12px blur, #000000 at 50%, 16px glow #1E3A5F at 20%
- **Large**: 8px offset, 24px blur, #000000 at 60%, 32px glow #1E3A5F at 25%
- **Overlay**: 16px offset, 48px blur, #000000 at 70%
- **Alert**: 20px glow #E63946 at 40%, 6px glow #E63946 at 60%

## Components

### Buttons
#### Variants
- **Primary**: #1E3A5F fill, #F1F5F9 text, no border, #264A75 fill, 4px radius, Subtle shadow. Hover: #FFFFFF.
- **Secondary**: #334155 fill, #94A3B8 text, 1px #64748B border, #475569 fill, 4px radius, no shadow. Hover: #F1F5F9.
- **Ghost**: transparent fill, #94A3B8 text, no border, #1E293B fill, 4px radius, no shadow. Hover: #F1F5F9.
- **Destructive**: #E63946 fill, #FFFFFF text, no border, #FF4D5A fill, 4px radius, Alert shadow. Hover: #FFFFFF.
#### Sizes
Sizes: Small (28px, 10px, 12px, 600), Medium (34px, 16px, 13px, 600), Large (40px, 20px, 14px, 600).
#### Disabled State
0.35 opacity.
- disabled cursor
- No shadow, no hover change

### Cards
- **Default**: #1E293B fill, 1px #334155 border, 4px radius, Subtle shadow, 16px padding.
- **Elevated**: #334155 fill, no border, 4px radius, Medium shadow, 16px padding.
2px outline #3B82F6 offset 2px focus-visible. Hover: border shifts to #64748B (200ms ease).

### Inputs
#### Text Input
- **Default**: #0F172A fill, 1px #334155 border, #F1F5F9 text, no shadow.
- **Hover**: #0F172A fill, 1px #64748B border, #F1F5F9 text, no shadow.
- **Focus**: #0F172A fill, 2px #3B82F6 border, #F1F5F9 text, Subtle shadow.
- **Error**: #0F172A fill, 2px #E63946 border, #F1F5F9 text, Alert shadow.
- **Disabled**: #1E293B fill, 1px #1E293B border, #64748B text, no shadow.
4px corners. 34px tall, 8px/12px padding, ** 12px / 600 weight / #94A3B8 / 4px bottom margin **label, ** 11px / 400 weight / #64748B / 4px top margin **helper text.

### Chips
#### Filter Chip
#334155 fill, #94A3B8 / 12px / 500 weight text, 1px #475569 border, 4px corners. 4px/10px padding. Active: Background #1E3A5F, Text #F1F5F9, Border #1E3A5F.
#### Status Chip
4px corners. 11px / 700 weight / uppercase. Background #E63946 at 15%, Text #FF6B76, Border 1px #E63946 at 30% critical, Background #F59E0B at 15%, Text #FBBF24, Border 1px #F59E0B at 30% warning, Background #22C55E at 15%, Text #4ADE80, Border 1px #22C55E at 30% normal, Background #3B82F6 at 15%, Text #60A5FA, Border 1px #3B82F6 at 30% info, 2px/8px padding.

### Lists
#### Default Item
13px / 400 / #F1F5F9 text. 40px tall, 8px/12px padding, 1px #1E293B divider, 11px / 400 / #64748B secondary text. Hover: Background #1E293B. Selected: Background #1E3A5F at 40%, left border 2px #3B82F6.

### Checkboxes
16px x 16px, 2px #64748B border, 2px corners. Checked: Background #1E3A5F, border #3B82F6, checkmark #F1F5F9. Indeterminate: Background #1E3A5F, dash #F1F5F9. Disabled: Background #1E293B, border #334155, 40% opacity. Labels in 13px / 400 / #94A3B8 6px left gap.

### Radio Buttons
16px x 16px, 2px #64748B border. Selected: Border #3B82F6, inner dot 8px #3B82F6. Disabled: Border #334155, 40% opacity. Labels in 13px / 400 / #94A3B8 6px left gap.

### Tooltips
#F1F5F9 fill, #0F172A / 12px / 400 weight text, 4px corners. 6px/10px padding, 220px max width, 5px triangle, matching background arrow, 300ms show, 0ms hide delay, fade + 2px translateY, 100ms ease animation.
---

## Do's and Don'ts

1. **Do** establish a clear alert hierarchy: Critical (red #E63946), Warning (amber #F59E0B), Info (blue #3B82F6), Normal (green #22C55E).
2. **Do** give vital data (heart rate, SpO2, BP) the highest visual prominence with large mono numerals.
3. **Don't** use red for anything other than critical/destructive states; reserve it so it always commands attention.
4. **Do** design for real-time update patterns with smooth value transitions, not jarring number jumps.
5. **Do** ensure all text meets WCAG AAA contrast (7:1) against the dark background for clinical readability.
6. **Don't** use decorative animations in monitoring views; motion should only communicate data changes.
7. **Do** provide compact, data-dense layouts that minimize scrolling during time-sensitive workflows.
8. **Don't** hide critical information behind hover states or expandable sections in monitoring dashboards.
9. **Do** design clear scan-zone layouts so clinicians can read vitals in a predictable left-to-right, top-to-bottom sweep.
10. **Don't** rely on color alone for alerts; always pair with iconography, labels, and optional audible indicators.