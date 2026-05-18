---
description: Conventions for React components
paths:
  - "src/components/**/*.tsx"
  - "src/components/**/*.ts"
---

# React component conventions

These rules apply when editing files under `src/components/`.

## Component style

- Use **functional components with hooks**. No class components.
- Default to named exports: `export function Button(...)`. Reserve default
  exports for page-level components only.
- Props interfaces are defined inline above the component, named
  `<ComponentName>Props`.

## State management

- Use `useState` for component-local state.
- For state shared across siblings, lift to the nearest common parent.
- Do not introduce Redux, MobX, or Zustand without architectural review.

## Event handling

- Event handlers are named `handle<Event>` (e.g., `handleClick`).
- Define them as `const handleX = () => {...}` inside the component body,
  not as inline arrow functions in JSX (for readability and testability).

## Accessibility

- Every interactive element must be keyboard-accessible.
- Buttons must have visible labels OR explicit `aria-label` attributes.
- Form inputs must have associated `<label>` elements.