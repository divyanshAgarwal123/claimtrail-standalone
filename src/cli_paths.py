"""Host-configured CLI boundaries for accidental agent-supplied paths and options."""
from __future__ import annotations

import os
import re
import shutil
from pathlib import Path


def allowed_path(value: Path, root: Path | None = None) -> Path:
    """The host sets the approved root outside the agent's CLI arguments."""
    base = (root or Path(os.environ.get("CLAIMTRAIL_ALLOWED_ROOT", Path.cwd()))).resolve(strict=True)
    candidate = value.expanduser().resolve()
    if not candidate.is_relative_to(base):
        raise ValueError("path is outside the host-approved root: " + str(value))
    return candidate


def python_executable(value: str | Path) -> str:
    text = str(value)
    if not text or text.startswith("-") or "\0" in text:
        raise ValueError("invalid executable argument")
    found = shutil.which(text)
    if not found:
        raise ValueError("executable is not installed: " + text)
    path = Path(found).absolute()
    pattern = r"python(?:\d+(?:\.\d+)*)?(?:\.exe)?"
    if not re.fullmatch(pattern, path.name) or not path.is_file():
        raise ValueError("expected an installed Python executable")
    return str(path)
