from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET


OOXML_NS = {
    "cp": "http://schemas.openxmlformats.org/package/2006/metadata/core-properties",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
    "ep": "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties",
    "cust": "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties",
    "vt": "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "w14": "http://schemas.microsoft.com/office/word/2010/wordml",
    "w15": "http://schemas.microsoft.com/office/word/2012/wordml",
    "ds": "http://schemas.openxmlformats.org/officeDocument/2006/customXml",
}


def make_json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, dict):
        return {str(k): make_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [make_json_safe(v) for v in value]
    return str(value)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def namespace_uri(tag: str) -> str | None:
    if tag.startswith("{") and "}" in tag:
        return tag[1:].split("}", 1)[0]
    return None


def read_xml(z: zipfile.ZipFile, member: str) -> ET.Element | None:
    try:
        return ET.fromstring(z.read(member))
    except Exception:
        return None


def decode_xml_bytes(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-16", "utf-16-le", "utf-16-be"):
        try:
            text = data.decode(enc)
            if "<" in text:
                return text
        except UnicodeError:
            pass
    return data.decode("utf-8", errors="replace")


def elem_value(root: ET.Element | None, xpath: str) -> str | None:
    if root is None:
        return None
    node = root.find(xpath, OOXML_NS)
    if node is None:
        return None
    return (node.text or "").strip() or None


def _parse_docx_zip(z: zipfile.ZipFile) -> dict[str, Any]:
    out: dict[str, Any] = {
        "type": "docx",
        "embedded_metadata": {},
        "word_internals": {},
        "custom_xml": [],
    }
    names = set(z.namelist())

    core = read_xml(z, "docProps/core.xml") if "docProps/core.xml" in names else None
    core_fields = {
        "creator": "dc:creator",
        "title": "dc:title",
        "subject": "dc:subject",
        "description": "dc:description",
        "keywords": "cp:keywords",
        "category": "cp:category",
        "content_status": "cp:contentStatus",
        "last_modified_by": "cp:lastModifiedBy",
        "revision": "cp:revision",
        "last_printed": "cp:lastPrinted",
        "created": "dcterms:created",
        "modified": "dcterms:modified",
    }
    out["embedded_metadata"]["core"] = {
        k: elem_value(core, v)
        for k, v in core_fields.items()
        if elem_value(core, v) is not None
    }

    app = read_xml(z, "docProps/app.xml") if "docProps/app.xml" in names else None
    app_fields = [
        "Template", "TotalTime", "Pages", "Words", "Characters", "CharactersWithSpaces",
        "Application", "AppVersion", "DocSecurity", "Lines", "Paragraphs", "Company",
        "SharedDoc", "HyperlinksChanged", "LinksUpToDate", "HyperlinkBase",
    ]
    app_values: dict[str, Any] = {}
    if app is not None:
        for field in app_fields:
            node = app.find(f"ep:{field}", OOXML_NS)
            if node is None:
                continue
            text = (node.text or "").strip()
            if text.isdigit():
                app_values[field] = int(text)
            elif text.lower() in {"true", "false"}:
                app_values[field] = text.lower() == "true"
            elif text != "" or field in {"Company", "HyperlinkBase"}:
                app_values[field] = text
    out["embedded_metadata"]["application"] = app_values

    custom_props: dict[str, Any] = {}
    if "docProps/custom.xml" in names:
        custom = read_xml(z, "docProps/custom.xml")
        if custom is not None:
            for prop in custom.findall("cust:property", OOXML_NS):
                name = prop.attrib.get("name")
                child = next(iter(prop), None)
                if name and child is not None:
                    custom_props[name] = (child.text or "").strip()
    out["embedded_metadata"]["custom_properties"] = custom_props

    settings = read_xml(z, "word/settings.xml") if "word/settings.xml" in names else None
    if settings is not None:
        zoom = settings.find("w:zoom", OOXML_NS)
        tab = settings.find("w:defaultTabStop", OOXML_NS)
        rsid_root = settings.find("w:rsids/w:rsidRoot", OOXML_NS)
        rsids = [
            n.attrib.get(f"{{{OOXML_NS['w']}}}val")
            for n in settings.findall("w:rsids/w:rsid", OOXML_NS)
        ]
        rsids = [x for x in rsids if x]
        word_internals = {
            "zoom_percent": zoom.attrib.get(f"{{{OOXML_NS['w']}}}percent") if zoom is not None else None,
            "default_tab_stop_twips": tab.attrib.get(f"{{{OOXML_NS['w']}}}val") if tab is not None else None,
            "track_changes_enabled": settings.find("w:trackRevisions", OOXML_NS) is not None,
            "do_not_track_formatting": settings.find("w:doNotTrackFormatting", OOXML_NS) is not None,
            "rsid_root": rsid_root.attrib.get(f"{{{OOXML_NS['w']}}}val") if rsid_root is not None else None,
            "settings_rsid_count": len(set(rsids)),
            "settings_rsids": sorted(set(rsids)),
        }
        doc_ids = {}
        for prefix in ("w14", "w15"):
            node = settings.find(f"{prefix}:docId", OOXML_NS)
            if node is not None:
                uri = OOXML_NS[prefix]
                doc_ids[prefix] = node.attrib.get(f"{{{uri}}}val")
        if doc_ids:
            word_internals["document_ids"] = doc_ids
        out["word_internals"].update({k: v for k, v in word_internals.items() if v is not None})

    doc = read_xml(z, "word/document.xml") if "word/document.xml" in names else None
    revision_counts: dict[str, int] = {}
    body_rsids: set[str] = set()
    if doc is not None:
        for tag in ("ins", "del", "moveFrom", "moveTo"):
            revision_counts[tag] = len(doc.findall(f".//w:{tag}", OOXML_NS))
        rsid_attr_names = {
            f"{{{OOXML_NS['w']}}}rsidR",
            f"{{{OOXML_NS['w']}}}rsidRDefault",
            f"{{{OOXML_NS['w']}}}rsidP",
            f"{{{OOXML_NS['w']}}}rsidDel",
            f"{{{OOXML_NS['w']}}}rsidRPr",
        }
        for node in doc.iter():
            for attr, value in node.attrib.items():
                if attr in rsid_attr_names and value:
                    body_rsids.add(value)
    out["word_internals"].update({
        "surviving_revision_markup": revision_counts,
        "body_rsid_count": len(body_rsids),
        "body_rsids": sorted(body_rsids),
        "comments_part_present": "word/comments.xml" in names,
        "people_part_present": "word/people.xml" in names,
    })

    item_names = sorted(n for n in names if re.fullmatch(r"customXml/item\d+\.xml", n))
    for item_name in item_names:
        match = re.search(r"item(\d+)\.xml$", item_name)
        if not match:
            continue
        num = match.group(1)
        props_name = f"customXml/itemProps{num}.xml"
        raw = z.read(item_name)
        text = decode_xml_bytes(raw)
        entry: dict[str, Any] = {"part": item_name, "bytes": len(raw)}

        root = None
        try:
            root = ET.fromstring(raw)
        except Exception:
            try:
                root = ET.fromstring(text.encode("utf-8"))
            except Exception:
                pass

        if root is not None:
            entry["root_element"] = local_name(root.tag)
            entry["root_namespace"] = namespace_uri(root.tag)
            if root.attrib:
                entry["root_attributes"] = {local_name(k): v for k, v in root.attrib.items()}

        if props_name in names:
            props = read_xml(z, props_name)
            if props is not None:
                refs = []
                for ref in props.findall(".//ds:schemaRef", OOXML_NS):
                    uri = ref.attrib.get(f"{{{OOXML_NS['ds']}}}uri")
                    if uri:
                        refs.append(uri)
                if refs:
                    entry["schema_refs"] = refs

        is_imanage = "imanage.com" in text.lower() or any(
            "imanage.com" in x.lower() for x in entry.get("schema_refs", [])
        )
        if root is not None and (is_imanage or len(raw) < 30000):
            leaves: dict[str, Any] = {}
            for node in root.iter():
                if len(list(node)) != 0:
                    continue
                value = (node.text or "").strip()
                if not value or len(value) > 2000:
                    continue
                key = local_name(node.tag)
                if key in leaves:
                    if not isinstance(leaves[key], list):
                        leaves[key] = [leaves[key]]
                    leaves[key].append(value)
                else:
                    leaves[key] = value
            if leaves:
                entry["leaf_values"] = leaves
        if is_imanage:
            entry["document_management_system"] = "iManage"
        out["custom_xml"].append(entry)

    out["package"] = {
        "part_count": len(names),
        "custom_xml_part_count": len(item_names),
    }
    return out


def parse_docx_bytes(data: bytes) -> dict[str, Any]:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        return _parse_docx_zip(z)


def parse_docx_path(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as z:
        return _parse_docx_zip(z)


def _parse_pdf_reader(reader: Any) -> dict[str, Any]:
    out: dict[str, Any] = {
        "type": "pdf",
        "embedded_metadata": {},
        "pdf_internals": {},
    }
    info = reader.metadata
    out["embedded_metadata"]["info_dictionary"] = (
        {str(k): make_json_safe(v) for k, v in info.items()} if info else {}
    )

    xmp = reader.xmp_metadata
    if xmp is not None:
        xmp_fields = {
            "dc_creator": getattr(xmp, "dc_creator", None),
            "dc_title": getattr(xmp, "dc_title", None),
            "dc_subject": getattr(xmp, "dc_subject", None),
            "xmp_creator_tool": getattr(xmp, "xmp_creator_tool", None),
            "xmp_create_date": getattr(xmp, "xmp_create_date", None),
            "xmp_modify_date": getattr(xmp, "xmp_modify_date", None),
            "xmp_metadata_date": getattr(xmp, "xmp_metadata_date", None),
            "xmpmm_document_id": getattr(xmp, "xmpmm_document_id", None),
            "xmpmm_instance_id": getattr(xmp, "xmpmm_instance_id", None),
            "pdf_producer": getattr(xmp, "pdf_producer", None),
            "pdf_keywords": getattr(xmp, "pdf_keywords", None),
            "pdf_pdfversion": getattr(xmp, "pdf_pdfversion", None),
            "custom_properties": getattr(xmp, "custom_properties", None),
        }
        out["embedded_metadata"]["xmp"] = {
            k: make_json_safe(v)
            for k, v in xmp_fields.items()
            if v not in (None, {}, [], "")
        }

    page_sizes = []
    for p in reader.pages:
        try:
            page_sizes.append({
                "width_points": float(p.mediabox.width),
                "height_points": float(p.mediabox.height),
            })
        except Exception:
            pass

    trailer_id = None
    try:
        ids = reader.trailer.get("/ID")
        if ids:
            trailer_id = [make_json_safe(x) for x in ids]
    except Exception:
        pass

    out["pdf_internals"] = {
        "page_count": len(reader.pages),
        "encrypted": reader.is_encrypted,
        "page_sizes": page_sizes,
        "trailer_id": trailer_id,
    }
    return out


def parse_pdf_bytes(data: bytes) -> dict[str, Any]:
    from pypdf import PdfReader
    return _parse_pdf_reader(PdfReader(io.BytesIO(data), strict=False))


def parse_pdf_path(path: Path) -> dict[str, Any]:
    from pypdf import PdfReader
    return _parse_pdf_reader(PdfReader(str(path), strict=False))


def inspect_bytes(data: bytes, filename: str) -> dict[str, Any]:
    suffix = Path(filename).suffix.lower()
    result: dict[str, Any] = {
        "file": filename,
        "sha256": sha256_bytes(data),
        "size_bytes": len(data),
    }
    try:
        if suffix == ".docx":
            result.update(parse_docx_bytes(data))
        elif suffix == ".pdf":
            result.update(parse_pdf_bytes(data))
        else:
            result.update({"type": "unsupported", "error": "Supported types: .docx, .pdf"})
    except Exception as exc:
        result.update({"type": suffix.lstrip(".") or "unknown", "error": f"{type(exc).__name__}: {exc}"})
    return make_json_safe(result)


def inspect_path(path: Path | str) -> dict[str, Any]:
    path = Path(path).expanduser().resolve()
    result: dict[str, Any] = {
        "file": str(path),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
        "filesystem_metadata": {
            "mtime": datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(),
            "ctime": datetime.fromtimestamp(path.stat().st_ctime).astimezone().isoformat(),
        },
    }
    try:
        if path.suffix.lower() == ".docx":
            result.update(parse_docx_path(path))
        elif path.suffix.lower() == ".pdf":
            result.update(parse_pdf_path(path))
        else:
            result.update({"type": "unsupported", "error": "Supported types: .docx, .pdf"})
    except Exception as exc:
        result.update({"type": path.suffix.lower().lstrip(".") or "unknown", "error": f"{type(exc).__name__}: {exc}"})
    return make_json_safe(result)


def timeline_events(result: dict[str, Any]) -> list[dict[str, str]]:
    """Return explicit timestamp-bearing metadata without inventing chronology."""
    events: list[dict[str, str]] = []
    typ = result.get("type")
    embedded = result.get("embedded_metadata", {})

    if typ == "docx":
        core = embedded.get("core", {})
        for key, label in (
            ("created", "DOCX created"),
            ("modified", "DOCX modified"),
            ("last_printed", "DOCX last printed"),
        ):
            if core.get(key):
                events.append({"timestamp": str(core[key]), "event": label, "source": f"docProps/core.xml:{key}"})
        for item in result.get("custom_xml", []):
            leaves = item.get("leaf_values", {})
            for key in ("lastmodified", "lastModified", "modified", "created"):
                value = leaves.get(key)
                if value:
                    values = value if isinstance(value, list) else [value]
                    for v in values:
                        events.append({
                            "timestamp": str(v),
                            "event": f"Custom XML {key}",
                            "source": item.get("part", "customXml"),
                        })
    elif typ == "pdf":
        info = embedded.get("info_dictionary", {})
        for key, label in (("/CreationDate", "PDF creation date"), ("/ModDate", "PDF modification date")):
            if info.get(key):
                events.append({"timestamp": str(info[key]), "event": label, "source": f"PDF Info {key}"})
        xmp = embedded.get("xmp", {})
        for key, label in (
            ("xmp_create_date", "XMP create date"),
            ("xmp_modify_date", "XMP modify date"),
            ("xmp_metadata_date", "XMP metadata date"),
        ):
            if xmp.get(key):
                events.append({"timestamp": str(xmp[key]), "event": label, "source": f"XMP {key}"})
        custom = xmp.get("custom_properties", {}) if isinstance(xmp.get("custom_properties", {}), dict) else {}
        for key, value in custom.items():
            if "modified" in str(key).lower() or "created" in str(key).lower() or "date" in str(key).lower():
                events.append({"timestamp": str(value), "event": str(key), "source": "XMP custom property"})
    return events


def provenance_clues(result: dict[str, Any]) -> list[str]:
    """Concise observations tied directly to extracted fields."""
    clues: list[str] = []
    typ = result.get("type")
    embedded = result.get("embedded_metadata", {})

    if typ == "docx":
        core = embedded.get("core", {})
        if core.get("creator"):
            clues.append(f"Embedded creator: {core['creator']}")
        if core.get("last_modified_by"):
            clues.append(f"Last modified by: {core['last_modified_by']}")
        if core.get("last_printed"):
            clues.append(f"Last printed metadata survives: {core['last_printed']}")
        app = embedded.get("application", {})
        if app.get("TotalTime") is not None:
            clues.append(f"Word TotalTime: {app['TotalTime']} minute(s)")
        wi = result.get("word_internals", {})
        if wi.get("track_changes_enabled"):
            clues.append("Track Changes is enabled in Word settings")
        revisions = wi.get("surviving_revision_markup", {})
        if revisions and any(revisions.values()):
            clues.append(f"Surviving tracked revision markup: {revisions}")
        if wi.get("settings_rsid_count"):
            clues.append(f"Word settings contain {wi['settings_rsid_count']} unique RSID(s)")
        for item in result.get("custom_xml", []):
            if item.get("document_management_system"):
                clues.append(f"Custom XML identifies document-management system: {item['document_management_system']}")
            leaves = item.get("leaf_values", {})
            for key in ("documentid", "senderemail", "database"):
                if key in leaves:
                    clues.append(f"Custom XML {key}: {leaves[key]}")
    elif typ == "pdf":
        info = embedded.get("info_dictionary", {})
        for key, label in (("/Author", "Author"), ("/Creator", "Creator"), ("/Producer", "Producer")):
            if info.get(key):
                clues.append(f"{label}: {info[key]}")
        xmp = embedded.get("xmp", {})
        if xmp.get("xmpmm_document_id"):
            clues.append(f"XMP document ID: {xmp['xmpmm_document_id']}")
        if xmp.get("xmpmm_instance_id"):
            clues.append(f"XMP instance ID: {xmp['xmpmm_instance_id']}")
    return clues


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract embedded provenance metadata from DOCX/PDF files.")
    parser.add_argument("files", nargs="+", help="DOCX/PDF files to inspect")
    parser.add_argument("--indent", type=int, default=2, help="JSON indentation")
    args = parser.parse_args()

    results = []
    for raw in args.files:
        path = Path(raw).expanduser().resolve()
        if not path.exists():
            results.append({"file": str(path), "error": "File not found"})
        else:
            results.append(inspect_path(path))
    print(json.dumps(results, indent=args.indent, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
