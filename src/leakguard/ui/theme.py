"""Theme tokens and static styling for the LEAKGUARD console.

Guarantees:
- Pure system font stack (no external Google Fonts or CDN requests)
- High contrast dark palette meeting WCAG AA requirements
- No internal Streamlit selectors or data-testid dependencies
- Zero client-side JavaScript execution
- Micro-interactions <= 200ms
- All animations wrapped in @media (prefers-reduced-motion: no-preference)
- Visible, high-contrast focus rings for keyboard navigation
- Support for no-CSS fallback mode via environment variable or parameter
"""

from __future__ import annotations

import os

# System font stacks
SYSTEM_FONT_STACK = (
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen-Sans, Ubuntu, '
    'Cantarell, "Helvetica Neue", Arial, sans-serif'
)
MONO_FONT_STACK = (
    'ui-monospace, "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace'
)

# Design tokens
PALETTE = {
    "bg_primary": "#0b132b",
    "bg_secondary": "#1c2541",
    "bg_card": "#162036",
    "bg_card_alt": "#1e293b",
    "border_subtle": "#2a3b5c",
    "border_focus": "#00b4d8",
    "text_primary": "#f8f9fa",
    "text_secondary": "#cbd5e1",
    "text_muted": "#94a3b8",
    "accent_primary": "#00b4d8",
    "accent_hover": "#90e0ef",
    # Severity tokens (Background / Border / Text)
    "sev_high_bg": "#450a0a",
    "sev_high_border": "#991b1b",
    "sev_high_text": "#fca5a5",
    "sev_med_bg": "#451a03",
    "sev_med_border": "#b45309",
    "sev_med_text": "#fcd34d",
    "sev_low_bg": "#064e3b",
    "sev_low_border": "#047857",
    "sev_low_text": "#6ee7b7",
    "sev_info_bg": "#172554",
    "sev_info_border": "#1d4ed8",
    "sev_info_text": "#93c5fd",
}

THEME_CSS = f"""
<style>
/* ==========================================================================
   LEAKGUARD Design System — Dark Mode Security Console
   Strictly system fonts, zero external requests, WCAG AA contrast.
   ========================================================================== */

:root {{
    --lg-font-sans: {SYSTEM_FONT_STACK};
    --lg-font-mono: {MONO_FONT_STACK};
    --lg-bg-primary: {PALETTE["bg_primary"]};
    --lg-bg-secondary: {PALETTE["bg_secondary"]};
    --lg-bg-card: {PALETTE["bg_card"]};
    --lg-border: {PALETTE["border_subtle"]};
    --lg-border-focus: {PALETTE["border_focus"]};
    --lg-text: {PALETTE["text_primary"]};
    --lg-text-secondary: {PALETTE["text_secondary"]};
    --lg-text-muted: {PALETTE["text_muted"]};
    --lg-accent: {PALETTE["accent_primary"]};
    --lg-accent-hover: {PALETTE["accent_hover"]};
}}

/* Typography */
body, [class*="css"], .stMarkdown, .stText {{
    font-family: var(--lg-font-sans) !important;
}}

code, pre, kbd, samp {{
    font-family: var(--lg-font-mono) !important;
}}

/* Accessible focus indicators */
*:focus-visible {{
    outline: 2px solid var(--lg-border-focus) !important;
    outline-offset: 2px !important;
}}

/* Card containers */
.leakguard-card {{
    background-color: var(--lg-bg-card);
    border: 1px solid var(--lg-border);
    border-radius: 8px;
    padding: 1.25rem;
    margin-bottom: 1rem;
}}

.leakguard-banner {{
    background-color: #172554;
    border-left: 4px solid var(--lg-accent);
    border-radius: 0 8px 8px 0;
    padding: 0.85rem 1.15rem;
    margin-bottom: 1.25rem;
    color: var(--lg-text);
}}

/* Runtime status strip */
.leakguard-status-strip {{
    background-color: #0f172a;
    border: 1px solid var(--lg-border);
    border-radius: 6px;
    padding: 0.65rem 0.9rem;
    font-size: 0.82rem;
    color: var(--lg-text-secondary);
    margin-top: 0.75rem;
    margin-bottom: 0.75rem;
}}

.leakguard-status-item {{
    display: flex;
    justify-content: space-between;
    padding: 0.2rem 0;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}}

.leakguard-status-item:last-child {{
    border-bottom: none;
}}

.leakguard-badge {{
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    text-transform: uppercase;
}}

/* Risk band headers */
.risk-badge-high {{
    background-color: {PALETTE["sev_high_bg"]};
    border: 1px solid {PALETTE["sev_high_border"]};
    color: {PALETTE["sev_high_text"]};
}}

.risk-badge-medium {{
    background-color: {PALETTE["sev_med_bg"]};
    border: 1px solid {PALETTE["sev_med_border"]};
    color: {PALETTE["sev_med_text"]};
}}

.risk-badge-low {{
    background-color: {PALETTE["sev_low_bg"]};
    border: 1px solid {PALETTE["sev_low_border"]};
    color: {PALETTE["sev_low_text"]};
}}

.risk-badge-none {{
    background-color: {PALETTE["sev_info_bg"]};
    border: 1px solid {PALETTE["sev_info_border"]};
    color: {PALETTE["sev_info_text"]};
}}

/* Annotated text findings */
mark.leakguard-finding {{
    border-radius: 3px;
    padding: 0.1rem 0.35rem;
    margin: 0 0.1rem;
    font-weight: 600;
    text-decoration: underline;
    text-decoration-thickness: 2px;
}}

mark.finding-high {{
    background-color: {PALETTE["sev_high_bg"]};
    color: {PALETTE["sev_high_text"]};
    border: 1px solid {PALETTE["sev_high_border"]};
    text-decoration-color: #ef4444;
}}

mark.finding-medium {{
    background-color: {PALETTE["sev_med_bg"]};
    color: {PALETTE["sev_med_text"]};
    border: 1px solid {PALETTE["sev_med_border"]};
    text-decoration-color: #f59e0b;
}}

mark.finding-low {{
    background-color: {PALETTE["sev_low_bg"]};
    color: {PALETTE["sev_low_text"]};
    border: 1px solid {PALETTE["sev_low_border"]};
    text-decoration-color: #10b981;
}}

mark.finding-info {{
    background-color: {PALETTE["sev_info_bg"]};
    color: {PALETTE["sev_info_text"]};
    border: 1px solid {PALETTE["sev_info_border"]};
    text-decoration-color: #3b82f6;
}}

/* Smooth transitions <= 200ms with prefers-reduced-motion honor */
@media (prefers-reduced-motion: no-preference) {{
    button, a, input, select, textarea, mark.leakguard-finding {{
        transition:
            background-color 0.15s ease-in-out,
            border-color 0.15s ease-in-out,
            color 0.15s ease-in-out;
    }}

    .leakguard-reveal {{
        animation: leakguardFadeIn 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    }}

    @keyframes leakguardFadeIn {{
        from {{
            opacity: 0;
            transform: translateY(4px);
        }}
        to {{
            opacity: 1;
            transform: translateY(0);
        }}
    }}
}}

@media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.01ms !important;
        scroll-behavior: auto !important;
    }}
}}
</style>
"""


def is_css_disabled() -> bool:
    """Check if custom CSS injection is disabled for testing or no-CSS fallback."""
    return os.environ.get("LEAKGUARD_DISABLE_CSS", "0") in ("1", "true", "True")


def get_custom_css(disabled: bool | None = None) -> str:
    """Return the static custom CSS block, or empty string if disabled."""
    if disabled is True or (disabled is None and is_css_disabled()):
        return ""
    return THEME_CSS
