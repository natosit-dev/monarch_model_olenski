from __future__ import annotations

import importlib
import os
import sys
import zipfile
import xml.etree.ElementTree as ET
from io import BytesIO
from pathlib import Path
from typing import Any


class DocHistoryUnavailable(RuntimeError):
    """Raised when the reusable doc_history package cannot be imported."""


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _candidate_doc_history_roots() -> tuple[Path, ...]:
    """Return local locations where the sibling doc_history repo may live.

    DiScO does not copy doc_history's extraction logic. It imports the package
    directly, preferring a normal installed import and then looking for the
    user's local sibling checkout.
    """

    candidates: list[Path] = []
    configured = os.environ.get("DOC_HISTORY_PATH")
    if configured:
        candidates.append(Path(configured).expanduser())

    repo_root = _repo_root()
    candidates.extend(
        [
            repo_root.parent / "doc_history",
            Path.home() / "doc_history",
        ]
    )

    # Preserve order while removing duplicates.
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve()) if candidate.exists() else str(candidate)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return tuple(unique)


def _load_doc_history_module():
    try:
        return importlib.import_module("doc_history")
    except ModuleNotFoundError:
        pass

    for root in _candidate_doc_history_roots():
        if not (root / "doc_history" / "__init__.py").exists():
            continue
        root_text = str(root.resolve())
        if root_text not in sys.path:
            sys.path.insert(0, root_text)
        try:
            return importlib.import_module("doc_history")
        except ModuleNotFoundError:
            continue

    searched = ", ".join(str(path) for path in _candidate_doc_history_roots())
    raise DocHistoryUnavailable(
        "DiScO could not import doc_history. Clone/install natosit-dev/doc_history "
        f"or set DOC_HISTORY_PATH. Searched: {searched}"
    )


def inspect_document_artifact(data: bytes, filename: str) -> dict[str, Any]:
    """Reuse doc_history and return its complete artifact/provenance dataset."""

    module = _load_doc_history_module()
    result = module.inspect_bytes(data, filename)
    return {
        "source_type": "file",
        "filename": filename,
        "doc_history": result,
        "timeline_events": module.timeline_events(result),
        "provenance_clues": module.provenance_clues(result),
    }


def _extract_docx_text(data: bytes) -> str:
    """Extract DOCX body text directly from OOXML with the standard library.

    DiScO only needs deterministic plain text for scoring, so it does not need
    python-docx here. Reading word/document.xml directly also avoids conflicts
    with the obsolete PyPI package named ``docx``.
    """

    word_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    p_tag = f"{{{word_ns}}}p"
    t_tag = f"{{{word_ns}}}t"
    tab_tag = f"{{{word_ns}}}tab"
    break_tags = {f"{{{word_ns}}}br", f"{{{word_ns}}}cr"}

    with zipfile.ZipFile(BytesIO(data)) as archive:
        xml_bytes = archive.read("word/document.xml")

    root = ET.fromstring(xml_bytes)
    blocks: list[str] = []
    for paragraph in root.iter(p_tag):
        parts: list[str] = []
        for node in paragraph.iter():
            if node.tag == t_tag and node.text:
                parts.append(node.text)
            elif node.tag == tab_tag:
                parts.append("\t")
            elif node.tag in break_tags:
                parts.append("\n")
        text = "".join(parts).strip()
        if text:
            blocks.append(text)
    return "\n".join(blocks)


def extract_document_text(data: bytes, filename: str) -> str:
    """Extract text for DiScO scoring without changing doc_history metadata.

    doc_history remains the provenance/metadata authority. This helper only
    supplies the plain text consumed by the existing DiScO text engine.
    """

    suffix = Path(filename).suffix.lower()

    if suffix == ".docx":
        return _extract_docx_text(data)

    if suffix == ".pdf":
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data), strict=False)
        return "\n".join((page.extract_text() or "") for page in reader.pages)

    raise ValueError("DiScO file upload currently supports .docx and .pdf files.")
