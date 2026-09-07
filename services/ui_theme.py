"""
services/ui_theme.py

FORGE Visual System -- injects a dark, glassmorphic, futuristic theme over
the default Streamlit chrome via CSS only. No application logic changes:
this module is purely presentational and safe to import from app.py without
touching any service, model, or state behavior.

Design language:
  - Background: near-black deep space gradient with a slow-drifting aurora glow
  - Typography: 'Space Grotesk' for display/headings, 'Inter' for body text
  - Accent: cyan -> violet -> magenta gradient (the "Forge Arc")
  - Surfaces: frosted glass panels (blurred, translucent, thin glowing border)
  - Motion: soft easing on hover/focus, a slow ambient pulse on the active step

Severity language: every colored indicator in the app (fact-strength tiers,
completeness-flag severity, contradiction severity) now routes through
render_severity_badge() below, so "red/amber/green/info" always means the
same three CSS variables everywhere, instead of each call site inventing
its own bracket-icon convention.
"""
import streamlit as st

THEME_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');

:root {
    --forge-bg: #05070d;
    --forge-bg-2: #0a0e1a;
    --forge-surface: rgba(255, 255, 255, 0.035);
    --forge-surface-strong: rgba(255, 255, 255, 0.06);
    --forge-border: rgba(140, 180, 255, 0.16);
    --forge-border-strong: rgba(140, 180, 255, 0.32);
    --forge-text: #e8edf7;
    --forge-muted: #8b93a8;
    --forge-cyan: #22d3ee;
    --forge-violet: #8b5cf6;
    --forge-magenta: #ec4899;
    --forge-green: #34d399;
    --forge-amber: #fbbf24;
    --forge-red: #f87171;
    --forge-gradient: linear-gradient(120deg, var(--forge-cyan) 0%, var(--forge-violet) 55%, var(--forge-magenta) 100%);
}

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, sans-serif;
}

.stApp {
    background:
        radial-gradient(1200px circle at 15% -10%, rgba(34, 211, 238, 0.10), transparent 55%),
        radial-gradient(1000px circle at 110% 10%, rgba(139, 92, 246, 0.10), transparent 50%),
        radial-gradient(900px circle at 50% 120%, rgba(236, 72, 153, 0.08), transparent 55%),
        linear-gradient(180deg, var(--forge-bg) 0%, var(--forge-bg-2) 100%);
    background-attachment: fixed;
    color: var(--forge-text);
    animation: forge-aurora 24s ease-in-out infinite alternate;
}

@keyframes forge-aurora {
    0%   { background-position: 0% 0%, 100% 0%, 50% 100%, 0 0; }
    100% { background-position: 8% 4%, 92% 6%, 46% 96%, 0 0; }
}

h1, h2, h3, h4, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    font-family: 'Space Grotesk', sans-serif !important;
    letter-spacing: -0.01em;
}

.forge-hero {
    padding: 8px 0 4px 0;
}
.forge-hero .forge-wordmark {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    font-size: 2.6rem;
    line-height: 1.1;
    background: var(--forge-gradient);
    background-size: 200% 200%;
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: forge-shimmer 6s ease infinite;
    margin: 0;
}
@keyframes forge-shimmer {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
.forge-hero .forge-tagline {
    font-family: 'Inter', sans-serif;
    font-weight: 500;
    letter-spacing: 0.24em;
    text-transform: uppercase;
    font-size: 0.72rem;
    color: var(--forge-muted);
    margin-top: 2px;
}
.forge-hero .forge-underline {
    height: 2px;
    width: 96px;
    margin-top: 10px;
    border-radius: 2px;
    background: var(--forge-gradient);
    background-size: 200% 200%;
    animation: forge-shimmer 6s ease infinite;
    box-shadow: 0 0 12px rgba(139, 92, 246, 0.55);
}

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: var(--forge-surface);
    border: 1px solid var(--forge-border);
    border-radius: 18px;
    backdrop-filter: blur(14px);
    -webkit-backdrop-filter: blur(14px);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35);
    transition: border-color 0.35s ease, box-shadow 0.35s ease, transform 0.25s ease;
}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {
    border-color: var(--forge-border-strong);
    box-shadow: 0 8px 40px rgba(34, 211, 238, 0.12), 0 0 0 1px rgba(139, 92, 246, 0.10) inset;
    transform: translateY(-1px);
}

.stButton > button {
    border-radius: 12px !important;
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    letter-spacing: 0.01em;
    border: 1px solid var(--forge-border) !important;
    background: var(--forge-surface-strong) !important;
    color: var(--forge-text) !important;
    transition: all 0.28s cubic-bezier(0.2, 0.8, 0.2, 1);
    box-shadow: 0 2px 12px rgba(0,0,0,0.25);
}
.stButton > button:hover {
    border-color: var(--forge-cyan) !important;
    box-shadow: 0 0 0 1px var(--forge-cyan) inset, 0 6px 24px rgba(34, 211, 238, 0.25);
    transform: translateY(-2px);
}
.stButton > button[kind="primary"] {
    background: var(--forge-gradient) !important;
    background-size: 200% 200% !important;
    border: none !important;
    color: #05070d !important;
    font-weight: 700;
    animation: forge-shimmer 8s ease infinite;
    box-shadow: 0 6px 24px rgba(139, 92, 246, 0.35);
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 10px 32px rgba(236, 72, 153, 0.4);
    transform: translateY(-2px) scale(1.01);
}
.stButton > button:disabled {
    opacity: 0.35 !important;
    transform: none !important;
    box-shadow: none !important;
}

.stFormSubmitButton > button {
    background: var(--forge-gradient) !important;
    background-size: 200% 200% !important;
    border: none !important;
    color: #05070d !important;
    font-weight: 700;
    border-radius: 12px !important;
    animation: forge-shimmer 8s ease infinite;
}

.stTextInput input, .stTextArea textarea, .stNumberInput input,
.stDateInput input, div[data-baseweb="select"] > div {
    background: var(--forge-surface) !important;
    border: 1px solid var(--forge-border) !important;
    border-radius: 10px !important;
    color: var(--forge-text) !important;
    transition: border-color 0.25s ease, box-shadow 0.25s ease;
}
.stTextInput input:focus, .stTextArea textarea:focus,
div[data-baseweb="select"] > div:focus-within {
    border-color: var(--forge-cyan) !important;
    box-shadow: 0 0 0 3px rgba(34, 211, 238, 0.15) !important;
}

.stRadio label, .stCheckbox label, .stMultiSelect label {
    color: var(--forge-text) !important;
}

.stProgress > div > div {
    background: var(--forge-gradient) !important;
    background-size: 200% 200% !important;
    animation: forge-shimmer 4s ease infinite;
    box-shadow: 0 0 14px rgba(34, 211, 238, 0.55);
    border-radius: 8px !important;
}
.stProgress > div {
    background: rgba(255,255,255,0.06) !important;
    border-radius: 8px !important;
}

div[data-testid="stAlert"] {
    border-radius: 14px !important;
    backdrop-filter: blur(10px);
    border: 1px solid var(--forge-border) !important;
    background: var(--forge-surface) !important;
}
div[data-testid="stAlertContentInfo"] { color: var(--forge-cyan) !important; }
div[data-testid="stAlertContentSuccess"] { color: var(--forge-green) !important; }
div[data-testid="stAlertContentWarning"] { color: var(--forge-amber) !important; }
div[data-testid="stAlertContentError"] { color: var(--forge-red) !important; }

details[data-testid="stExpander"] {
    background: var(--forge-surface) !important;
    border: 1px solid var(--forge-border) !important;
    border-radius: 14px !important;
    backdrop-filter: blur(10px);
}
details[data-testid="stExpander"] summary {
    font-weight: 600;
    color: var(--forge-text) !important;
}

.stTable, div[data-testid="stTable"] {
    border-radius: 14px;
    overflow: hidden;
    border: 1px solid var(--forge-border);
}
.stTable table, div[data-testid="stTable"] table {
    background: var(--forge-surface) !important;
}
.stTable thead tr th, div[data-testid="stTable"] thead tr th {
    background: rgba(139, 92, 246, 0.18) !important;
    color: var(--forge-text) !important;
    font-family: 'Space Grotesk', sans-serif;
    text-transform: uppercase;
    font-size: 0.72rem;
    letter-spacing: 0.06em;
}
.stTable tbody tr td, div[data-testid="stTable"] tbody tr td {
    color: var(--forge-text) !important;
    border-color: rgba(255,255,255,0.06) !important;
}
.stTable tbody tr:hover td, div[data-testid="stTable"] tbody tr:hover td {
    background: rgba(34, 211, 238, 0.06) !important;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(10,14,26,0.98) 0%, rgba(5,7,13,0.98) 100%) !important;
    border-right: 1px solid var(--forge-border);
}
section[data-testid="stSidebar"] * { color: var(--forge-text); }

.forge-stepper { margin-top: 4px; }
.forge-step {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 7px 4px;
    position: relative;
}
.forge-step .forge-dot {
    width: 10px; height: 10px; border-radius: 50%;
    background: rgba(255,255,255,0.14);
    border: 1px solid var(--forge-border);
    flex-shrink: 0;
    transition: all 0.3s ease;
}
.forge-step.done .forge-dot {
    background: var(--forge-green);
    box-shadow: 0 0 8px rgba(52, 211, 153, 0.6);
    border-color: transparent;
}
.forge-step.active .forge-dot {
    background: var(--forge-cyan);
    box-shadow: 0 0 0 4px rgba(34, 211, 238, 0.18), 0 0 14px rgba(34, 211, 238, 0.75);
    border-color: transparent;
    animation: forge-pulse 1.8s ease-in-out infinite;
}
@keyframes forge-pulse {
    0%   { box-shadow: 0 0 0 4px rgba(34, 211, 238, 0.18), 0 0 14px rgba(34, 211, 238, 0.55); }
    50%  { box-shadow: 0 0 0 7px rgba(34, 211, 238, 0.08), 0 0 20px rgba(34, 211, 238, 0.85); }
    100% { box-shadow: 0 0 0 4px rgba(34, 211, 238, 0.18), 0 0 14px rgba(34, 211, 238, 0.55); }
}
.forge-step .forge-label {
    font-size: 0.86rem;
    font-weight: 500;
    color: var(--forge-muted);
}
.forge-step.active .forge-label { color: var(--forge-text); font-weight: 600; }
.forge-step.done .forge-label { color: var(--forge-text); }
.forge-step:not(:last-child)::before {
    content: "";
    position: absolute;
    left: 8.5px;
    top: 26px;
    width: 1px;
    height: 20px;
    background: var(--forge-border);
}

.forge-chip {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 4px 12px;
    border-radius: 999px;
    background: var(--forge-surface);
    border: 1px solid var(--forge-border);
    font-size: 0.78rem;
    color: var(--forge-muted);
}
.forge-chip .forge-chip-value {
    font-family: 'Space Grotesk', sans-serif;
    font-weight: 700;
    background: var(--forge-gradient);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}

.forge-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 2px 10px;
    border-radius: 999px;
    border: 1px solid currentColor;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    background: rgba(255,255,255,0.03);
}
.forge-badge::before {
    content: "";
    width: 6px; height: 6px; border-radius: 50%;
    background: currentColor;
    box-shadow: 0 0 6px currentColor;
}

::-webkit-scrollbar { width: 10px; height: 10px; }
::-webkit-scrollbar-track { background: var(--forge-bg); }
::-webkit-scrollbar-thumb {
    background: rgba(139, 92, 246, 0.35);
    border-radius: 8px;
}
::-webkit-scrollbar-thumb:hover { background: rgba(139, 92, 246, 0.55); }

hr {
    border: none;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--forge-border-strong), transparent);
    margin: 1.4rem 0;
}
</style>
"""

SEVERITY_COLOR_VAR = {
    "strong": "var(--forge-green)", "moderate": "var(--forge-amber)", "weak": "var(--forge-red)",
    "green": "var(--forge-green)", "amber": "var(--forge-amber)", "red": "var(--forge-red)",
    "high": "var(--forge-red)", "medium": "var(--forge-amber)", "low": "var(--forge-cyan)",
    "info": "var(--forge-cyan)",
}


def inject_theme():
    """Call once near the top of app.py, immediately after st.set_page_config().
    Pure presentation -- does not touch session_state, services, or models."""
    st.markdown(THEME_CSS, unsafe_allow_html=True)


def render_hero(title: str = "FORGE", tagline: str = "Educated. Organized. Never Alone."):
    """Gradient-animated wordmark hero, replacing plain st.title/st.caption."""
    st.markdown(
        f"""
        <div class="forge-hero">
            <div class="forge-wordmark">{title}</div>
            <div class="forge-tagline">{tagline}</div>
            <div class="forge-underline"></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stepper(step_labels: dict, current_step: int, extra_step_label: str = None,
                    extra_step_active: bool = False):
    """Renders the sidebar step tracker as a glowing vertical stepper instead
    of plain markdown bullets."""
    rows = []
    for n, label in step_labels.items():
        if extra_step_active:
            css_class = "done"
        elif n < current_step:
            css_class = "done"
        elif n == current_step:
            css_class = "active"
        else:
            css_class = ""
        rows.append(
            f'<div class="forge-step {css_class}"><div class="forge-dot"></div>'
            f'<div class="forge-label">{n}. {label}</div></div>'
        )
    if extra_step_label:
        css_class = "active" if extra_step_active else ""
        rows.append(
            f'<div class="forge-step {css_class}"><div class="forge-dot"></div>'
            f'<div class="forge-label">{extra_step_label}</div></div>'
        )
    st.markdown(f'<div class="forge-stepper">{"".join(rows)}</div>', unsafe_allow_html=True)


def render_chip(label: str, value: str):
    """Small glass pill used for the Foundation-strength readout."""
    st.markdown(
        f'<div class="forge-chip">{label}: <span class="forge-chip-value">{value}</span></div>',
        unsafe_allow_html=True,
    )


def render_severity_badge(label: str, severity_key: str):
    """Small glowing pill for any severity/strength indicator in the app.
    `severity_key` should be one of the keys in SEVERITY_COLOR_VAR (fact
    strength tiers, or completeness/contradiction severity vocabularies).
    Falls back to muted gray for an unrecognized key rather than guessing
    a color."""
    color = SEVERITY_COLOR_VAR.get(severity_key, "var(--forge-muted)")
    st.markdown(
        f'<span class="forge-badge" style="color:{color};">{label}</span>',
        unsafe_allow_html=True,
    )
