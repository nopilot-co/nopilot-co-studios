"""``learnings doctor`` — report whether the learnings store is wired up."""

from __future__ import annotations

import os
import shutil

from . import __version__, learnings_dir


def doctor() -> dict:
    d = learnings_dir()
    writable = False
    try:
        d.mkdir(parents=True, exist_ok=True)
        writable = os.access(d, os.W_OK)
    except OSError:
        writable = False
    return {
        "version": __version__,
        "learnings_cli": shutil.which("learnings"),
        "learnings_dir": str(d),
        "dir_writable": writable,
    }
