#!/usr/bin/env python3
"""
Shared utilities for scrapers and scripts.

Provides common functions used across the pipeline:
- Environment variable loading (.env file support)
- Text normalization for name comparison
- Name similarity scoring
"""

import os
import re

_UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_UTILS_DIR)


def load_env_var(key):
    """Load a variable from environment first, then .env file.

    Handles quoted values in .env (strips surrounding ' or ").
    Returns None if not found.
    """
    value = os.environ.get(key)
    if value:
        return value

    env_path = os.path.join(PROJECT_ROOT, ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def normalize(text):
    """Normalize text for comparison — lowercase, strip non-alphanumeric."""
    if not text:
        return ""
    return re.sub(r'[^a-z0-9]', '', text.lower())


def normalize_artist(name):
    """Normalize an artist name for fuzzy comparison.

    Richer than normalize() — also strips 'the', tour suffixes,
    parentheticals, and normalizes separators.
    """
    if not name:
        return ""
    name = name.lower().strip()
    name = re.sub(r"^the\s+", "", name)
    name = re.sub(
        r"\s*[-–—]\s*(tour|us tour|headline tour|album release).*$",
        "", name, flags=re.IGNORECASE,
    )
    name = re.sub(r"\s*\(.*?\)", "", name)
    name = re.sub(r"\s*/\s*", " ", name)
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def name_similarity(a, b):
    """Score how similar two names are. Returns a float 0-1.

    Checks exact match, containment, and token overlap.
    """
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    # Containment — but only if lengths are similar
    if na in nb or nb in na:
        length_ratio = min(len(na), len(nb)) / max(len(na), len(nb))
        if length_ratio >= 0.5:
            return 0.9
        return 0.3

    # Token overlap
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    overlap = len(tokens_a & tokens_b)
    total = max(len(tokens_a), len(tokens_b))
    return overlap / total
