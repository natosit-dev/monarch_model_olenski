"""Document provenance metadata extraction."""

from .extractor import inspect_bytes, inspect_path, timeline_events, provenance_clues

__all__ = ["inspect_bytes", "inspect_path", "timeline_events", "provenance_clues"]
