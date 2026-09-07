"""
services/db.py

Supabase client + authentication for FORGE.

CRITICAL: A Supabase client holding an authenticated session must NEVER be
cached with st.cache_resource or any other cross-session cache. Streamlit
cached resources are shared across every visitor's session on the same
server process -- caching an authenticated client would let one user's
database session leak into another user's browser tab. Every function here
either creates a fresh, unauthenticated client (safe to reuse for the
anon-key connection itself) or operates on a client instance stored in
st.session_state, which Streamlit guarantees is private to one browser
session.

Once a user is authenticated, every table read/write automatically goes
through the Row Level Security policies already defined on the FORGE
Supabase project (case_profiles.user_id = auth.uid(), and every other table
cascades ownership through case_id). This module does not need to add its
own "WHERE user_id = ..." filtering -- the database enforces isolation
regardless of what the application code does or forgets to do, which is a
stronger guarantee than relying on application-level filtering alone.
"""
from __future__ import annotations
import os
from typing import Optional
import streamlit as st
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://vmjfgdsldenfnijhofcg.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY")


def get_session_client() -> Client:
    """Returns THIS browser session's own Supabase client, created once and
    stored in st.session_state. Never shared across sessions. Safe to call
    repeatedly -- only creates the client on first call per session."""
    if "supabase_client" not in st.session_state:
        if not SUPABASE_KEY:
            raise RuntimeError(
                "SUPABASE_KEY (or SUPABASE_ANON_KEY) environment variable is not set. "
                "FORGE cannot connect to the database without it."
            )
        st.session_state.supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return st.session_state.supabase_client


def sign_up(email: str, password: str) -> dict:
    """Returns {'success': bool, 'message': str, 'user_id': str|None}.
    Never raises -- all Supabase Auth errors are caught and returned as a
    user-facing message, since this is called directly from Streamlit forms."""
    client = get_session_client()
    try:
        result = client.auth.sign_up({"email": email, "password": password})
        if result.user is None:
            return {"success": False, "message": "Sign-up did not return a user. Please try again.", "user_id": None}
        return {
            "success": True,
            "message": "Account created. Check your email to confirm your address if required, then sign in.",
            "user_id": result.user.id,
        }
    except Exception as e:
        return {"success": False, "message": f"Sign-up failed: {e}", "user_id": None}


def sign_in(email: str, password: str) -> dict:
    """Returns {'success': bool, 'message': str, 'user_id': str|None}.
    On success, stores the session (access_token/refresh_token) in
    st.session_state so it survives Streamlit reruns within this browser
    session -- but never anywhere shared across sessions."""
    client = get_session_client()
    try:
        result = client.auth.sign_in_with_password({"email": email, "password": password})
        if result.user is None or result.session is None:
            return {"success": False, "message": "Invalid email or password.", "user_id": None}
        st.session_state.auth_user_id = result.user.id
        st.session_state.auth_user_email = result.user.email
        st.session_state.auth_access_token = result.session.access_token
        st.session_state.auth_refresh_token = result.session.refresh_token
        return {"success": True, "message": "Signed in.", "user_id": result.user.id}
    except Exception as e:
        return {"success": False, "message": f"Sign-in failed: {e}", "user_id": None}


def sign_out() -> None:
    """Clears this session's auth state. Does not affect any other
    session -- each browser session has its own st.session_state."""
    client = get_session_client()
    try:
        client.auth.sign_out()
    except Exception:
        pass
    for key in ("auth_user_id", "auth_user_email", "auth_access_token", "auth_refresh_token"):
        st.session_state.pop(key, None)


def restore_session_if_present() -> Optional[str]:
    """Call at the top of every rerun. If this browser session already has
    stored tokens (from an earlier sign-in this session), re-attaches them
    to the client so RLS-scoped queries keep working after a Streamlit
    rerun. Returns the authenticated user_id, or None if not signed in."""
    if "auth_access_token" not in st.session_state:
        return None
    client = get_session_client()
    try:
        client.auth.set_session(
            st.session_state.auth_access_token,
            st.session_state.auth_refresh_token,
        )
        return st.session_state.get("auth_user_id")
    except Exception:
        for key in ("auth_user_id", "auth_user_email", "auth_access_token", "auth_refresh_token"):
            st.session_state.pop(key, None)
        return None


def current_user_id() -> Optional[str]:
    return st.session_state.get("auth_user_id")


def current_user_email() -> Optional[str]:
    return st.session_state.get("auth_user_email")
