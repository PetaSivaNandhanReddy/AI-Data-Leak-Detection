"""Proxy view forwarding to labs.security_lab for LEAKGUARD."""

from __future__ import annotations

from labs.security_lab import render_security_lab

if __name__ == "__main__" or "streamlit" in __name__:
    render_security_lab()
