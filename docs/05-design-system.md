# Design System

## Design Direction

Calm, trustworthy, data-first energy dashboard. The interface should make high usage obvious without looking alarming, and should explain every number in plain language.

## Color Palette

| Purpose | Color | Use |
| --- | --- | --- |
| Primary energy green | `#16A34A` | Primary actions, positive savings, healthy usage |
| Deep green | `#166534` | Hover/active states, headings |
| Energy amber | `#D97706` | Approaching budget or elevated usage |
| Alert red | `#DC2626` | Threshold breach, error, urgent warning |
| Insight blue | `#2563EB` | Informational AI/forecast cards |
| Page background | `#F8FAFC` | Main light background |
| Surface | `#FFFFFF` | Cards, dialogs, inputs |
| Primary text | `#0F172A` | Headings and body copy |
| Secondary text | `#475569` | Labels, timestamps, helper text |
| Border | `#E2E8F0` | Card and input borders |

Never use red and green as the only way to convey status; pair color with an icon and text label.

## Typography

- Font family: Inter, with `system-ui, sans-serif` fallback.
- Page title: 30px / 700.
- Section title: 20px / 600.
- Card metric: 28px / 700, tabular numbers when available.
- Body: 14–16px / 400.
- Label/caption: 12–14px / 500.
- Use `kWh`, `₹`, date ranges, and rates with clear units.

## Layout and Spacing

- Maximum content width: 1280px; horizontal padding 16px mobile, 24px desktop.
- Base spacing unit: 4px; use 8, 12, 16, 24, 32, and 48px increments.
- Desktop dashboard: 4 metric cards in a grid; tablet: 2; mobile: 1.
- Sidebar navigation on desktop; compact top navigation/drawer on mobile.
- Use 8px corner radius for inputs/buttons and 12px for cards.

## Theme

- Launch light mode first.
- Add dark mode only after the dashboard is stable; do not maintain partially styled themes.
- Honor `prefers-reduced-motion`.

## Core Components

### Buttons

- Primary: green filled, white text; for one primary action per view.
- Secondary: white surface, green border/text.
- Destructive: red only for irreversible actions.
- Disabled state must be visibly distinct and non-interactive.

### Cards

- White surface, `#E2E8F0` 1px border, subtle shadow only on hover where interactive.
- A metric card includes label, main value, unit, comparison/context, and a status indicator.

### Charts

- Line chart: energy consumption over time.
- Bar chart: device ranking.
- Do not rely on tooltips alone; include accessible labels/summaries.
- Label units and time ranges explicitly.

### Alerts and Insights

- Alert card: severity icon, short reason, measured value, threshold, timestamp, recommended action.
- Standby insight: display baseline watts, estimated monthly kWh/cost, confidence/data window, and a practical checklist.
- AI wording must be labelled “Suggestion” and visually separated from calculated facts.

## Accessibility

- Maintain WCAG AA text contrast.
- Keyboard-accessible controls with visible focus rings.
- Inputs need persistent labels, not placeholder-only labels.
- All charts need text alternatives/summaries.
- Errors need an explanation and an actionable retry/fix path.

