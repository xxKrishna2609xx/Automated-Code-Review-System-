"""
diff_utils.py
=============
Utilities for parsing, normalising, and manipulating unified Git diffs.

Author : AI Code Review Bot — Phase 4
"""

from __future__ import annotations

from typing import Optional


def normalise_diff(diff: str) -> str:
    """Normalise line endings and strip trailing whitespace per line.

    Steps:
    1. Replace Windows (\\r\\n) and legacy Mac (\\r) line endings with standard \\n.
    2. Strip trailing whitespace from each line while preserving leading whitespace
       and +/- diff indicators.

    Args:
        diff: Raw unified diff string.

    Returns:
        Normalised diff string.
    """
    diff_clean = diff.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in diff_clean.splitlines())


def detect_language_from_diff(diff: str) -> Optional[str]:
    """Heuristically detect the primary programming language from diff file headers.

    Parses ``--- a/path/to/file.ext`` and ``+++ b/path/to/file.ext`` lines
    to collect file extensions, then returns the name of the most frequent language.

    Args:
        diff: Normalised unified diff string.

    Returns:
        Human-readable language name (e.g. ``"Python"``), or ``None`` if inconclusive.
    """
    ext_to_language: dict[str, str] = {
        ".py": "Python",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".js": "JavaScript",
        ".jsx": "JavaScript",
        ".java": "Java",
        ".kt": "Kotlin",
        ".go": "Go",
        ".rs": "Rust",
        ".cpp": "C++",
        ".cc": "C++",
        ".c": "C",
        ".cs": "C#",
        ".rb": "Ruby",
        ".php": "PHP",
        ".swift": "Swift",
        ".scala": "Scala",
        ".sh": "Shell",
        ".yaml": "YAML",
        ".yml": "YAML",
        ".json": "JSON",
        ".sql": "SQL",
        ".tf": "Terraform",
        ".html": "HTML",
        ".css": "CSS",
    }

    extension_counts: dict[str, int] = {}
    for line in diff.splitlines():
        if line.startswith(("--- a/", "+++ b/", "--- ", "+++ ")):
            filename = line.split(" ", 1)[-1].strip()
            # Strip git prefixes like "a/" and "b/"
            filename = filename.lstrip("ab/")
            if "." in filename:
                ext = "." + filename.rsplit(".", 1)[-1].lower()
                if ext in ext_to_language:
                    extension_counts[ext] = extension_counts.get(ext, 0) + 1

    if not extension_counts:
        return None

    dominant_ext = max(extension_counts, key=extension_counts.__getitem__)
    return ext_to_language.get(dominant_ext)


def split_diff_into_chunks(diff: str, max_chars: int, overlap_lines: int) -> list[str]:
    """Split a large unified diff into overlapping string chunks.

    Each chunk stays under ``max_chars`` characters. Adjacent chunks share
    ``overlap_lines`` lines so context is preserved across boundaries.

    Args:
        diff         : Full unified diff string.
        max_chars    : Maximum character length per chunk.
        overlap_lines: Number of trailing lines from previous chunk to prepend to next.

    Returns:
        List of diff chunk strings. Returns a single-element list when diff fits in max_chars.
    """
    if len(diff) <= max_chars:
        return [diff]

    lines = diff.splitlines(keepends=True)
    chunks: list[str] = []
    current_lines: list[str] = []
    current_chars = 0

    for line in lines:
        if current_chars + len(line) > max_chars and current_lines:
            chunks.append("".join(current_lines))
            # Keep the last overlap_lines lines for context continuity
            overlap = current_lines[-overlap_lines:] if overlap_lines > 0 else []
            current_lines = list(overlap)
            current_chars = sum(len(l) for l in current_lines)

        current_lines.append(line)
        current_chars += len(line)

    if current_lines:
        chunks.append("".join(current_lines))

    return chunks
