# Geevi UI system

## Direction: Ink and Cobalt

Geevi uses a neutral cloud canvas, graphite text, white surfaces and a restrained cobalt accent. The wordmark is simply **geevi.** in Manrope, with a cobalt full stop. There is no separate G symbol.

The palette was compared in the working app against eucalyptus and muted plum. Cobalt was selected as a design judgment: primary actions stand apart from the green completion states, while the mostly neutral surfaces make dense records easier to scan. Eucalyptus made success states and branding harder to distinguish. Plum remained viable, but cobalt provided the clearest hierarchy in this workspace. These are design decisions, not findings from clinician usability research.

Open `palette-study.html` to compare all three directions in light and dark appearance. The application uses the selected palette; the comparison is kept outside the product workflow.

| Role | Light | Dark |
| --- | --- | --- |
| Action / brand | `oklch(48% .135 255)` | `oklch(79% .09 255)` |
| Canvas | `oklch(97.4% .002 255)` | `oklch(18% .009 255)` |
| Surface | `oklch(99.8% 0 none)` | `oklch(22% .012 255)` |
| Primary text | `oklch(27% .012 255)` | `oklch(95% .006 255)` |
| Secondary text | `oklch(45% .016 255)` | `oklch(76% .016 255)` |

Green, amber and red retain semantic roles. Every status also has a text label. They are never the only way to identify a state.

## Workflow changes

- **Today:** a compact overview, counts from actual owned work, category filters, and the next action at the front of each item. Supporting ownership details remain available. Links enter the relevant care or decision view.
- **Patients:** searchable, large clickable rows with identifier and episode context. No matches is distinct from an empty workspace.
- **Clinical overview:** current decision, recorded uncertainty and information awaited come before deeper findings. Source links remain beside findings. Assessment, goals and supporting detail expand on demand.
- **Plan & decisions:** focused views for the individual plan, applicability, patient discussion and exceptions. Missing prerequisites link to the relevant view. `All sections` restores the full record.
- **Care & follow-up:** focused views for handoff tasks, the care record, concerns and follow-up. Proposed care, performed care and administrative scheduling keep their existing meanings.
- **Reports:** separate views for source documents, verification and gaps, and document receipt. Successful receipt links straight into review of the received document.
- **Research:** questions, published references and the evidence library are separate views. Study depth remains visible; findings and limitations expand together. Case-linked questions retain their origin.
- **All routes:** shared typography, form hierarchy, buttons, source viewer styling, tables, error states, loading feedback, responsive navigation and theme preference.

Focused panels remain mounted while hidden, so switching views does not discard local form entries. Hash links can open a specific section. Drafts are not persisted across page reloads or route changes. The server remains responsible for roles, provenance, approval gates, exact-version signatures, impact reviews and audit history.

## Interaction and accessibility

Manrope is bundled locally. Default body text is 16px; text inputs stay at 16px on mobile. Controls have 44px minimum height, with visible keyboard focus. Native disclosures and dialogs retain keyboard behavior. Workflow tabs support arrows, Home and End; navigation can be opened and closed by keyboard on narrow screens.

Motion uses short transform and opacity transitions: 180ms panel reveals, 240ms entry feedback and 130ms button response. There is no decorative background animation. All new motion is opt-in under `prefers-reduced-motion: no-preference`.

Light, dark and system appearance are available. Only the cosmetic `geevi-theme` preference is stored locally; patient and clinical records keep their existing server storage.

Measured in Chromium against rendered OKLCH colors:

| Contrast pair | Light | Dark |
| --- | ---: | ---: |
| Body text / surface | 14.89:1 | 14.99:1 |
| Secondary text / surface | 7.37:1 | 8.07:1 |
| Secondary text / canvas | 6.87:1 | 8.76:1 |
| Action link / surface | 6.56:1 | 8.99:1 |
| Primary button text / fill | 6.44:1 | 9.38:1 |
| Input boundary / surface | 3.61:1 | 3.87:1 |

This is a targeted contrast and keyboard check, not a claim of a complete accessibility certification.

## Implementation

- `apps/web/src/styles/tokens.css`: single semantic color and sizing source.
- `apps/web/src/styles/globals.css`: shared components, responsive layout and reduced-motion-aware interactions.
- `apps/web/src/components/brand.tsx`: text-only wordmark and patient/account initials.
- `apps/web/src/components/appearance.tsx`: appearance control.
- `apps/web/src/components/workflow-views.tsx`: persistent mounted panels and hash navigation.
- `tests/components/workflow-views.test.tsx` and `tests/e2e/ui-workflows.spec.ts`: draft retention, linked views, search, mobile navigation, theme and reduced motion.

The requested [good-css skill](https://github.com/vojtaholik/good-css) was installed at revision `92d436ba1937d1b1407c47e35abb3e199eaace2e` and applied to this implementation: OKLCH, `light-dark()`, derived tints, logical properties, intrinsic grid sizing, pointer-aware hover, explicit active/focus states, and opt-in motion. It is an authoring skill, not a runtime dependency.

The redesign was developed in an isolated worktree against a separate fictional preview database. Only reviewed frontend files, dependency changes and these design documents are transferred to the application. Existing backend behavior and supplied records are preserved.

## Verification on 11 October 2026

Verified after transfer in the original `geevi` folder:

- TypeScript and ESLint pass.
- 14 component tests pass, including draft retention and keyboard tab navigation.
- All 28 real-API browser tests pass in one final run (1.8 minutes), including the complete department journey, exact source regions, approval guards, recovery after API restart, original-byte import/export, mobile keyboard behavior, section links after sign-in, theme persistence and reduced motion.
- Production Next.js build succeeds.
- Rendered desktop, tablet (820px), mobile (390px) and small-phone (320px) checks show no page overflow. Source tables retain their own horizontal scrolling where needed.
- Palette-study buttons and light/dark control were exercised in the browser.

Checks used the installed Node 26.4 runtime; the repository currently declares Node 24.x. The local preview uses an isolated fictional database. Nothing was deployed externally.
