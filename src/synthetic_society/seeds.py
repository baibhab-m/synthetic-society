"""Seed loaders — India-specific data acquisition.

These are optional: the engine itself only needs a string seed. These
helpers pull richer real-world signals and turn them into seed text.

Each loader returns plain text. Plug them into `SyntheticSociety.run_full`
or feed them straight into the `GraphBuilder`.
"""

from __future__ import annotations

from . import consumer, political, campus, startup  # noqa: F401

__all__ = ["consumer", "political", "campus", "startup"]