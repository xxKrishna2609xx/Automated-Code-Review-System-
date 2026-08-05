"""
diff_mapper.py
==============
Unified diff patch parser and line-to-position mapping utility for GitHub Review API.

GitHub's REST API historically required a 1-based `position` index within the
diff patch string for inline comments. Modern GitHub Review API supports `path`,
`line`, `side="RIGHT"`, but `position` is still useful as a fallback or for classic APIs.

This module parses unified diff hunks (`@@ -old,count +new,count @@`) and computes
both line mapping and 1-based diff hunk positions reliably.

Author : AI Code Review Bot — Phase 5
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class LineMapping:
    """Mapping entry for a single line in a diff hunk."""

    position: int              # 1-based line position inside the patch
    new_line_no: Optional[int] # Line number in modified file (RIGHT side)
    old_line_no: Optional[int] # Line number in original file (LEFT side)
    line_type: str             # '+' (added), '-' (deleted), ' ' (context), 'header'


@dataclass
class DiffHunk:
    """Represents a single unified diff hunk."""

    header: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    hunk_position: int         # 1-based position of @@ line in full diff patch
    line_mappings: list[LineMapping] = field(default_factory=list)


@dataclass
class DiffFileMap:
    """Parsed patch map for a single file in a multi-file unified diff."""

    old_path: str
    new_path: str
    hunks: list[DiffHunk] = field(default_factory=list)
    line_to_position: dict[int, int] = field(default_factory=dict) # new_line -> position


_HUNK_RE = re.compile(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@")


def parse_unified_diff(diff_text: str) -> dict[str, DiffFileMap]:
    """Parse a full unified diff text into a dictionary of file path -> DiffFileMap.

    Args:
        diff_text: Full unified diff string containing diff headers and hunks.

    Returns:
        Dict mapping relative file paths to their parsed DiffFileMap structure.
    """
    files: dict[str, DiffFileMap] = {}
    if not diff_text or not diff_text.strip():
        return files

    current_file_path: Optional[str] = None
    current_file_map: Optional[DiffFileMap] = None
    position_counter = 0

    lines = diff_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]

        # File header: --- a/path
        if line.startswith("--- "):
            old_path = line[4:].strip().lstrip("a/")
            i += 1
            if i < len(lines) and lines[i].startswith("+++ "):
                new_path = lines[i][4:].strip().lstrip("b/")
                current_file_path = new_path if new_path != "/dev/null" else old_path
                current_file_map = DiffFileMap(old_path=old_path, new_path=current_file_path)
                files[current_file_path] = current_file_map
                position_counter = 0  # GitHub resets position per file patch
            i += 1
            continue

        # Hunk header: @@ -old,count +new,count @@
        hunk_match = _HUNK_RE.match(line)
        if hunk_match and current_file_map:
            position_counter += 1
            old_start = int(hunk_match.group(1))
            old_count = int(hunk_match.group(2)) if hunk_match.group(2) else 1
            new_start = int(hunk_match.group(3))
            new_count = int(hunk_match.group(4)) if hunk_match.group(4) else 1

            hunk = DiffHunk(
                header=line,
                old_start=old_start,
                old_count=old_count,
                new_start=new_start,
                new_count=new_count,
                hunk_position=position_counter,
            )

            current_old = old_start
            current_new = new_start
            i += 1

            while i < len(lines) and not lines[i].startswith("--- ") and not lines[i].startswith("@@ "):
                patch_line = lines[i]
                position_counter += 1

                if patch_line.startswith("+"):
                    hunk.line_mappings.append(
                        LineMapping(
                            position=position_counter,
                            new_line_no=current_new,
                            old_line_no=None,
                            line_type="+",
                        )
                    )
                    current_file_map.line_to_position[current_new] = position_counter
                    current_new += 1
                elif patch_line.startswith("-"):
                    hunk.line_mappings.append(
                        LineMapping(
                            position=position_counter,
                            new_line_no=None,
                            old_line_no=current_old,
                            line_type="-",
                        )
                    )
                    current_old += 1
                elif patch_line.startswith(" ") or patch_line == "":
                    hunk.line_mappings.append(
                        LineMapping(
                            position=position_counter,
                            new_line_no=current_new,
                            old_line_no=current_old,
                            line_type=" ",
                        )
                    )
                    current_file_map.line_to_position[current_new] = position_counter
                    current_new += 1
                    current_old += 1
                else:
                    # Ignore EOF markers (\ No newline at end of file)
                    pass

                i += 1

            current_file_map.hunks.append(hunk)
            continue

        i += 1

    return files


def map_line_to_diff_position(
    diff_text: str,
    file_path: str,
    target_line: int,
) -> tuple[Optional[int], int, str]:
    """Map a target file line number to GitHub diff position and side.

    Args:
        diff_text  : Full unified diff string.
        file_path  : Relative target file path.
        target_line: 1-indexed target line in the modified file.

    Returns:
        Tuple of ``(position, line, side)``:
        - ``position``: 1-based diff hunk position (or None if line not in patch).
        - ``line``    : Validated file line number.
        - ``side``    : "RIGHT" (default) or "LEFT".
    """
    file_maps = parse_unified_diff(diff_text)
    clean_path = file_path.lstrip("./").lstrip("a/").lstrip("b/")

    # Find matching file map
    matched_map = file_maps.get(clean_path)
    if not matched_map:
        # Search by suffix/basename matching
        for path_key, fmap in file_maps.items():
            if path_key.endswith(clean_path) or clean_path.endswith(path_key):
                matched_map = fmap
                break

    if not matched_map:
        return None, target_line, "RIGHT"

    # Check exact line match
    if target_line in matched_map.line_to_position:
        position = matched_map.line_to_position[target_line]
        return position, target_line, "RIGHT"

    # Fallback: Find closest line in patch
    if matched_map.line_to_position:
        closest_line = min(matched_map.line_to_position.keys(), key=lambda l: abs(l - target_line))
        position = matched_map.line_to_position[closest_line]
        return position, closest_line, "RIGHT"

    return None, target_line, "RIGHT"
