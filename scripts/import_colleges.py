#!/usr/bin/env python3
"""Reproduce the full eligible IPEDS directory, without network access by default.

The institutional directory is a source snapshot, not thousands of individually
researched organization profiles. Run --download explicitly to refresh sources.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]
YEAR = 2025
RETRIEVED_AT = "2026-10-24"
SOURCE_DIR = ROOT / "data" / "sources" / "ipeds"
OUTPUT = ROOT / "data" / "catalogs" / "ipeds.json"
SOURCE_URL = "https://nces.ed.gov/ipeds/complete-data-files/HD2025.zip"
DICTIONARY_URL = "https://nces.ed.gov/ipeds/complete-data-files/HD2025_Dict.zip"
METHOD_URL = "https://nces.ed.gov/ipeds/use-the-data/institutional-groupings-in-ipeds"
US_STATES_DC = frozenset("AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split())
REQUIRED = {"UNITID", "INSTNM", "STABBR", "CITY", "WEBADDR", "SECTOR", "ICLEVEL", "CONTROL", "DEGGRANT", "ACT", "CYACTIVE", "CLOSEDAT", "LATITUDE", "LONGITUD"}
SOURCE_FIELDS = ("CONTROL", "SECTOR", "ICLEVEL", "DEGGRANT", "HLOFFER", "HDEGOFR1", "INSTCAT", "ACT", "CYACTIVE", "POSTSEC", "PSEFLAG", "PSET4FLG", "CLOSEDAT", "NEWID", "WEBADDR", "F1SYSTYP", "F1SYSNAM", "F1SYSCOD", "ADDR", "ZIP")
SECTOR_LABELS = {"1": "公立 · 四年制及以上", "2": "私立非营利 · 四年制及以上", "3": "私立营利 · 四年制及以上", "4": "公立 · 两年至不足四年制", "5": "私立非营利 · 两年至不足四年制", "6": "私立营利 · 两年至不足四年制", "7": "公立 · 不足两年制", "8": "私立非营利 · 不足两年制", "9": "私立营利 · 不足两年制"}

# Explicit reviewed crosswalk: ID plus exact HD2025 source name; no fuzzy name
# matching, campus-to-system conflation, or automatic historical-name matching.
CURATED = {
    "110404": ("caltech", "California Institute of Technology"),
    "110635": ("uc-berkeley", "University of California-Berkeley"),
    "110644": ("uc-davis", "University of California-Davis"),
    "110653": ("uc-irvine", "University of California-Irvine"),
    "110662": ("uc-ucla", "University of California-Los Angeles"),
    "110671": ("uc-riverside", "University of California-Riverside"),
    "110680": ("uc-sandiego", "University of California-San Diego"),
    "110699": ("uc-sanfrancisco", "University of California-San Francisco"),
    "110705": ("uc-santabarbara", "University of California-Santa Barbara"),
    "110714": ("uc-santacruz", "University of California-Santa Cruz"),
    "130794": ("yale", "Yale University"),
    "134130": ("florida", "University of Florida"),
    "139755": ("georgia-tech", "Georgia Institute of Technology-Main Campus"),
    "144050": ("chicago", "University of Chicago"),
    "147767": ("northwestern", "Northwestern University"),
    "162928": ("johns-hopkins", "Johns Hopkins University"),
    "166027": ("harvard", "Harvard University"),
    "166683": ("mit", "Massachusetts Institute of Technology"),
    "170976": ("michigan", "University of Michigan-Ann Arbor"),
    "182670": ("dartmouth", "Dartmouth College"),
    "186131": ("princeton", "Princeton University"),
    "190150": ("columbia", "Columbia University in the City of New York"),
    "198419": ("duke", "Duke University"),
    "204796": ("ohio-state", "Ohio State University-Main Campus"),
    "215062": ("upenn", "University of Pennsylvania"),
    "217156": ("brown", "Brown University"),
    "228778": ("utexas-austin", "The University of Texas at Austin"),
    "236948": ("washington", "University of Washington-Seattle Campus"),
    "243744": ("stanford", "Stanford University"),
    "445188": ("uc-merced", "University of California-Merced"),
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_rows(path: Path) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(path.read_bytes().decode("utf-8-sig")))
    if not REQUIRED.issubset(reader.fieldnames or []):
        raise ValueError(f"Missing IPEDS columns: {sorted(REQUIRED - set(reader.fieldnames or []))}")
    rows, seen = [], set()
    for row in reader:
        unitid = row.get("UNITID", "")
        if not re.fullmatch(r"\d{6}", unitid) or not row.get("INSTNM", "").strip():
            raise ValueError(f"Invalid UNITID or name: {unitid!r}")
        if unitid in seen:
            raise ValueError(f"Duplicate UNITID: {unitid}")
        seen.add(unitid)
        rows.append(row)
    if not rows:
        raise ValueError("Empty IPEDS directory")
    return rows


def exclusion_reason(row: dict[str, str]) -> str | None:
    if row["STABBR"] not in US_STATES_DC:
        return "outside_50_states_dc"
    # CYACTIVE=1 also includes ACT=M (closed in survey year, still has data).
    if row["ACT"] not in {"A", "N", "R"} or row["CYACTIVE"] != "1":
        return "not_open_in_source_period"
    if row["CLOSEDAT"] not in {"", "-2"}:
        return "reported_closure"
    if row["SECTOR"] not in SECTOR_LABELS:
        return "administrative_or_unknown_sector"
    return None


def https_url(value: str) -> str | None:
    if any(c.isspace() for c in value):
        return None
    try:
        url = urlsplit(value)
        _ = url.port
        if url.scheme == "https" and url.hostname and "." in url.hostname and not url.username and not url.password:
            return value
    except ValueError:
        pass
    return None


def website(row: dict[str, str]) -> tuple[str | None, str]:
    raw = row.get("WEBADDR", "").strip()
    if https_url(raw):
        return raw, "source_explicit_https"
    # Bare hostnames are converted only when the same source row supplies an
    # HTTPS address on that exact host. No invented HTTPS for raw HTTP links.
    if raw and "://" not in raw and not raw.startswith("//"):
        proposed = https_url("https://" + raw)
        if proposed:
            host = urlsplit(proposed).hostname
            for field in ("ADMINURL", "FAIDURL", "APPLURL", "NPRICURL", "VETURL", "ATHURL", "DISAURL"):
                evidence = row.get(field, "").strip()
                if https_url(evidence) and urlsplit(evidence).hostname == host:
                    return proposed, "https_same_host_in_" + field.lower()
    return None, "raw_address_preserved_https_unverified" if raw else "not_reported"


def location(row: dict[str, str], registry_url: str) -> dict | None:
    try:
        lat, lon = float(row["LATITUDE"]), float(row["LONGITUD"])
    except (ValueError, TypeError):
        return None
    if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180 or (lat == 0 and lon == 0):
        return None
    return {"lat": lat, "lon": lon, "city": row["CITY"], "state": row["STABBR"], "precision": "campus", "evidence_url": registry_url}


def record(row: dict[str, str]) -> dict:
    unitid = row["UNITID"]
    registry_url = f"https://nces.ed.gov/collegenavigator/?id={unitid}"
    official_url, normalization = website(row)
    source_fields = {key.lower(): row.get(key, "") for key in SOURCE_FIELDS}
    source_fields["official_url_normalization"] = normalization
    if normalization.startswith("https_same_host_in_"):
        field = normalization.removeprefix("https_same_host_in_").upper()
        source_fields["official_url_https_evidence"] = row[field]
    aliases = list(dict.fromkeys(s.strip() for s in re.split(r"[|;]", row.get("IALIAS", "")) if s.strip() and s.strip() != row["INSTNM"]))
    result = {
        "id": f"ipeds-{unitid}", "name": row["INSTNM"], "name_zh": None,
        "domain": "university", "category": "university_campus", "jurisdiction": "US",
        "official_url": official_url, "registry_url": registry_url, "aliases": aliases,
        "identifiers": {"unitid": unitid}, "catalog_source": "ipeds", "record_kind": "directory",
        "city": row["CITY"], "state": row["STABBR"], "location": location(row, registry_url),
        "institution_type": SECTOR_LABELS[row["SECTOR"]] + (" · 学位授予" if row["DEGGRANT"] == "1" else " · 非学位教育"),
        "source_fields": source_fields,
    }
    match = CURATED.get(unitid)
    if match:
        if match[1] != row["INSTNM"]:
            raise ValueError(f"Curated crosswalk requires review: {unitid} {row['INSTNM']!r}")
        result["curated_id"] = match[0]
    return result


def build_catalog(path: Path, retrieved_at: str = RETRIEVED_AT) -> dict:
    rows = read_rows(path)
    reasons = Counter(exclusion_reason(row) for row in rows)
    records = [record(row) for row in rows if exclusion_reason(row) is None]
    records.sort(key=lambda item: item["identifiers"]["unitid"])
    outside = [row for row in rows if row["STABBR"] not in US_STATES_DC]
    metadata = {
        "id": "ipeds", "title": "NCES IPEDS HD2025 美国高等及职业教育机构目录",
        "source_url": SOURCE_URL, "retrieved_at": retrieved_at, "source_period": "2025–26 (HD2025 provisional directory)",
        "scope": "50 州及 DC，ACT=A/N/R、CYACTIVE=1、SECTOR=1..9、未报告关闭的教学机构；包括学位和非学位教育机构。",
        "license": "U.S. federal public-use data; NCES/IES attribution retained; factual directory records.",
        "license_url": "https://nces.ed.gov/about/public-access-research",
        "dictionary_url": DICTIONARY_URL, "methodology_url": METHOD_URL,
        "coverage_notes": [
            "按完整官方目录导入，无条数上限；这是 IPEDS 报告范围，不等于所有现实存在的美国教育组织。",
            "目录年份为 2025–26，2026-10-24 是下载日，不代表逐校核验当天仍在运营。",
            "学位授予机构包括副学士至博士教育，不能把全部目录条目称为四年制大学。",
            "原始文件保留领地、其他辖区、行政单位、关闭和并校条目；默认教学机构目录按明确规则筛选。",
            "FM、MH、PW 是自由联系国，其他辖区统计不把它们全部称为美国领地。",
            "校址坐标直接来自 NCES LATITUDE/LONGITUD，未重新地理编码；校园点不保证是所有校区或精确入口。",
            "官网字段仅接受来源明确 HTTPS，或同一行完全相同主机的其他官方字段明确 HTTPS；其余原地址保留，HTTPS 链接留空。",
            "机构名称、地址、类别和系统名称均为目录报告值；不自动生成治理、负责人、控制关系或金融流转。",
        ],
        "raw_count": len(rows), "included_count": len(records), "excluded_count": len(rows) - len(records),
        "sha256": digest(path.read_bytes()), "source_file": path.name,
        "raw_file": "data/sources/ipeds/" + path.name,
        "counts": {
            "raw_50_states_dc": len(rows) - len(outside),
            "outside_50_states_dc": len(outside),
            "outside_by_jurisdiction": dict(sorted(Counter(row["STABBR"] for row in outside).items())),
            "degree_granting": sum(r["source_fields"]["deggrant"] == "1" for r in records),
            "nondegree_granting": sum(r["source_fields"]["deggrant"] == "2" for r in records),
            "with_location": sum(r["location"] is not None for r in records),
            "with_https_official_url": sum(r["official_url"] is not None for r in records),
            "with_curated_match": sum("curated_id" in r for r in records),
            "by_state": dict(sorted(Counter(r["state"] for r in records).items())),
            "by_sector": dict(sorted(Counter(r["source_fields"]["sector"] for r in records).items())),
            "exclusions": {reason: count for reason, count in sorted(reasons.items(), key=lambda pair: str(pair[0])) if reason is not None},
        },
    }
    return {"metadata": metadata, "records": records}


def download_sources(destination: Path, retrieved_at: str) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    manifest = {"retrieved_at": retrieved_at, "source_period": "2025–26", "files": []}
    for url, member in ((SOURCE_URL, "hd2025.csv"), (DICTIONARY_URL, "hd2025.xlsx")):
        with urlopen(Request(url, headers={"User-Agent": "Institutional-Atlas public-directory-import/1.0"}), timeout=60) as response:
            payload = response.read()
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            raw = archive.read(member)
        (destination / member).write_bytes(raw)
        manifest["files"].append({"path": member, "source_url": url, "sha256": digest(raw), "download_archive_sha256": digest(payload), "bytes": len(raw)})
    (destination / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="Explicitly fetch official HD2025 data and dictionary before importing")
    parser.add_argument("--source", type=Path, default=SOURCE_DIR / "hd2025.csv")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--retrieved-at", default=RETRIEVED_AT)
    parser.add_argument("--check", action="store_true", help="Verify committed output reproduces exactly; do not rewrite")
    args = parser.parse_args()
    if args.download:
        download_sources(args.source.parent, args.retrieved_at)
    catalog = build_catalog(args.source, args.retrieved_at)
    rendered = json.dumps(catalog, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n"
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != rendered:
            raise SystemExit("IPEDS catalog is stale; run scripts/import_colleges.py")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(json.dumps({key: catalog["metadata"][key] for key in ("raw_count", "included_count", "excluded_count", "sha256")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
