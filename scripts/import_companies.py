#!/usr/bin/env python3
"""Rebuild the US-listed issuer-label catalog from official Nasdaq snapshots.

This is a directory import, not a legal-entity/CIK resolver.  Exact issuer labels
are grouped after removing explicitly recognizable security descriptions.
Unknown names are never fuzzy-joined, and funds are not called operating firms.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import urllib.request
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
URLS = {
    "nasdaqlisted.txt": "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt",
    "otherlisted.txt": "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt",
}
DEFINITIONS = "https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs"
# Unknown exchange codes remain source codes instead of guessed exchange names.
EXCHANGES = {"Q": "Nasdaq", "N": "NYSE", "A": "NYSE MKT / American", "P": "NYSE Arca", "Z": "BATS / Cboe", "V": "IEX"}
AUXILIARY = re.compile(
    r"\b(?:warrants?|rights|notes?\b|debentures?|mortgage\s+bonds?\b|bonds?\s+(?:due|\d)|ETNs?\b|"
    r"preferred\s+(?:stock|shares?|units?|securities|series|limited)|preference\s+(?:shares?|securities)|"
    r"pfd\b|prd\b|dep\s+shs\b|depositary\s+sh\b|"
    r"(?<!American )(?<!Global )Depos[ia]t(?:ary|ory)\s+Shares?\b|"
    r"units?,?\s+each\b|corporate\s+units\b|STRATS\b|CorTS\b)", re.I)
AUXILIARY_PREFIX = re.compile(
    r"^(?:\d|Depos[ia]t(?:ary|ory)\b|Dep\s+Shs\b|Preferred\b|Preference\b|"
    r"Non[- ]?Cumulative\b|Perpetual\b|Series\b|Notes\b|Debentures\b|"
    r"Warrants?\b|Redeemable\s+Warrants?\b|Rights\b|Units?\b|Corporate\s+Units\b|"
    r"First\s+Mortgage\b|Collateral\s+Trust\s+Mortgage\b|Income\s+Capital\s+Obligation\b)", re.I)
PRIMARY_SUFFIX = re.compile(
    r"(?:\s+|(?<=[.)]))(?:(?:New\s+)?(?:Common|Ordinary|Capital)\s+(?:Stock|Shares?|Units)\b|"
    r"Class\s+[A-Z0-9-]+\s+(?:(?:[A-Za-z-]+)\s+){0,7}(?:Stock|Shares?|Units)\b|"
    r"(?:American|Global)\s+Depos[ia]t(?:ary|ory)\s+(?:Shares?|Receipts)\b|"
    r"ADS\b|ADRs?\b|Shares\s+of\s+Beneficial\s+Interest\b|"
    r"Units\s+of\s+Beneficial\s+Interest\b|Limited\s+Partnership\s+Units\b|"
    r"(?:New\s+York|NY)\s+Registry\s+Shares\b|Subordinate\s+Voting\s+Shares\b|"
    r"Class\s+[A-Z0-9-]+\s+Sub\.\s+Vot\.|Class\s+[A-Z0-9-]+\s+Representing\s+Limited\s+Partner\s+Interests|"
    r"Class\s+[A-Z0-9-]+\s+Depositary\s+Receipts|"
    r"Series\s+[A-Z0-9-]+\s+Operating\s+Partnership\s+Units|Class\s+[A-Z0-9-]+\s*$|Units\s*$)", re.I)

# Source-name + ticker must both match.  A bank subsidiary is not the listed
# holding company.  XOM is intentionally absent: its new holding-company name
# differs from the existing Exxon Mobil Corporation profile.
CROSSWALK = {
    "AAPL": ("apple", "Apple Inc."),
    "GOOGL": ("alphabet", "Alphabet Inc."),
    "AMZN": ("amazon", "Amazon.com, Inc."),
    "BRK.A": ("berkshire-hathaway", "Berkshire Hathaway Inc."),
    "BA": ("boeing", "Boeing Company (The)"),
    "LLY": ("eli-lilly", "Eli Lilly and Company"),
    "JNJ": ("johnson-johnson", "Johnson & Johnson"),
    "META": ("meta", "Meta Platforms, Inc."),
    "MSFT": ("microsoft", "Microsoft Corporation"),
    "NVDA": ("nvidia", "NVIDIA Corporation"),
    "TSLA": ("tesla", "Tesla, Inc."),
    "WMT": ("walmart", "Walmart Inc."),
    "BAC": ("bofa-corp", "Bank of America Corporation"),
    "BLK": ("blackrock", "BlackRock, Inc."),
    "C": ("citigroup", "Citigroup, Inc."),
    "GS": ("goldman-sachs", "Goldman Sachs Group, Inc. (The)"),
    "JPM": ("jpmorgan-chase", "JP Morgan Chase & Co."),
    "MS": ("morgan-stanley", "Morgan Stanley"),
    "WFC": ("wells-fargo", "Wells Fargo & Company"),
}


def normalized_name(value: str) -> str:
    """Whitespace/case normalization only; no legal suffix or fuzzy matching."""
    return " ".join(value.split()).casefold()


def parse_file(path: Path):
    raw = path.read_bytes()
    text = raw.decode("utf-8-sig")
    lines = text.splitlines()
    if not lines or "Security Name" not in lines[0]:
        raise ValueError(f"Invalid Nasdaq header: {path.name}")
    trailers = [line for line in lines if line.startswith("File Creation Time:")]
    if len(trailers) != 1 or lines[-1] != trailers[0]:
        raise ValueError(f"Missing or misplaced Nasdaq timestamp: {path.name}")
    stamp = trailers[0].split("|", 1)[0].split(":", 1)[1].strip()
    date = datetime.strptime(stamp, "%m%d%Y%H:%M").isoformat(timespec="minutes")
    rows = list(csv.DictReader(io.StringIO("\n".join(lines[:-1])), delimiter="|"))
    expected = {"Security Name", "ETF", "Test Issue"}
    if not rows or not expected.issubset(rows[0]):
        raise ValueError(f"Invalid or empty Nasdaq directory: {path.name}")
    return rows, {"path": f"data/sources/sec/{path.name}", "sha256": hashlib.sha256(raw).hexdigest(), "source_url": URLS[path.name], "file_created_at": date, "row_count": len(rows)}


def primary_name(row, filename):
    name = " ".join(row["Security Name"].split())
    if filename == "nasdaqlisted.txt" and " - " in name:
        issuer, description = name.split(" - ", 1)
        # Nasdaq supplies the issuer before the delimiter, even for units.
        match = PRIMARY_SUFFIX.search(issuer)
        issuer = issuer[:match.start()] if match else issuer
        return issuer.strip(), bool(AUXILIARY.search(description))
    if AUXILIARY.search(name):
        return None, True
    match = PRIMARY_SUFFIX.search(name)
    issuer = name[:match.start()] if match else name
    return issuer.strip().rstrip(","), False


def listing(row, filename):
    symbol = row.get("Symbol") or row.get("ACT Symbol")
    code = "Q" if filename == "nasdaqlisted.txt" else row["Exchange"]
    return {"ticker": symbol, "exchange": EXCHANGES.get(code, f"Nasdaq directory code {code}"), "exchange_code": code,
            "security_name": row["Security Name"], "market_category": row.get("Market Category"),
            "financial_status": row.get("Financial Status"), "source_file": filename}


def build_catalog(source_dir: Path, retrieved_at: str):
    datetime.strptime(retrieved_at, "%Y-%m-%d")
    groups, pending, excluded, files = {}, [], [], []
    for filename in URLS:
        rows, metadata = parse_file(source_dir / filename)
        files.append(metadata)
        for row in rows:
            symbol = row.get("Symbol") or row.get("ACT Symbol")
            if not symbol or not row.get("Security Name") or row["Test Issue"] not in {"N", "Y"} or row["ETF"] not in {"N", "Y"}:
                raise ValueError(f"Malformed directory row: {filename} {symbol}")
            reason = "test_issue" if row["Test Issue"] == "Y" else "etf" if row["ETF"] == "Y" else None
            if reason:
                excluded.append({"ticker": symbol, "reason": reason, "source_file": filename})
                continue
            issuer, auxiliary = primary_name(row, filename)
            item = listing(row, filename)
            if auxiliary:
                pending.append((issuer, item))
                continue
            key = normalized_name(issuer)
            groups.setdefault(key, {"name": issuer, "listings": []})["listings"].append(item)

    # Auxiliary instruments attach only to an exact issuer label already backed
    # by a primary listing.  We never strip a ticker suffix and assume identity.
    ordered_keys = sorted(groups, key=len, reverse=True)
    for issuer, item in pending:
        key = normalized_name(issuer) if issuer else None
        if key not in groups:
            key = None
            security = normalized_name(item["security_name"])
            candidates = [candidate for candidate in ordered_keys
                          if security.startswith(candidate + " ") and
                          AUXILIARY_PREFIX.search(security[len(candidate):].strip()) and
                          AUXILIARY.search(security[len(candidate):])]
            if candidates:
                # The longest exact label avoids joining a subsidiary to a
                # similarly named parent, e.g. "X" versus "X Finance LLC".
                key = candidates[0]
        if key in groups:
            item["instrument_role"] = "auxiliary"
            groups[key]["listings"].append(item)
        else:
            excluded.append({"ticker": item["ticker"], "reason": "auxiliary_without_exact_primary_issuer", "security_name": item["security_name"], "source_file": item["source_file"]})

    records = []
    for key, group in sorted(groups.items()):
        group["listings"].sort(key=lambda value: (value["ticker"], value["exchange"]))
        symbols = [value["ticker"] for value in group["listings"]]
        source_files = sorted({value["source_file"] for value in group["listings"]})
        record = {
            "id": "nasdaq-issuer-" + hashlib.sha256(key.encode()).hexdigest()[:16],
            "name": group["name"], "name_zh": None,
            "domain": "enterprise", "category": "enterprise_group", "jurisdiction": "US-listed",
            "official_url": None, "registry_url": URLS[source_files[0]], "aliases": symbols,
            "identifiers": {"nasdaq_issuer_label": group["name"]}, "catalog_source": "nasdaq",
            "record_kind": "directory", "location": None, "listings": group["listings"],
            "institution_type": "美国上市发行人（公司、基金等；性质待核验）",
            "source_fields": {"issuer_resolution": "exact_directory_label", "domicile": None, "issuer_nature": "unverified", "source_files": source_files},
        }
        for symbol in symbols:
            match = CROSSWALK.get(symbol)
            if match and normalized_name(match[1]) == key:
                record["curated_id"] = match[0]
        records.append(record)
    reasons = Counter(value["reason"] for value in excluded)
    combined = hashlib.sha256()
    for info in files:
        combined.update(info["path"].encode() + b"\0" + info["sha256"].encode() + b"\n")
    included_securities = sum(len(record["listings"]) for record in records)
    raw_count = sum(info["row_count"] for info in files)
    assert raw_count == included_securities + len(excluded)
    assert len({record["id"] for record in records}) == len(records)
    metadata = {
        "id": "nasdaq", "title": "Nasdaq Trader 美国上市发行人名录",
        "source_url": DEFINITIONS, "retrieved_at": retrieved_at,
        "source_period": "; ".join(f"{Path(info['path']).name}: {info['file_created_at']} (Nasdaq 原文时间，未给时区)" for info in files),
        "scope": "Nasdaq 与 Other Exchange-Listed 官方证券目录；排除 ETF、测试记录；按明确发行人名称合并，附加可准确归属的辅助证券。包括外国发行人、封闭式基金及 SPAC，非美国本土经营公司全集。",
        "license": "Nasdaq public symbol directories; original Nasdaq rights and terms apply. No open-data license is asserted; project code license does not relicense source data.",
        "coverage_notes": [
            "SEC 全量文件直连返回 HTTP 403，本次没有绕过限制；改用 Nasdaq Trader 官方公开下载。",
            "included_count 是证券名称推导出的发行人标签组数，不是经 CIK/LEI 完全消歧的法人数量；只去空白和大小写，不做模糊合并。",
            "测试、ETF、无法归属到主证券发行人的债券/优先股/权证等保留排除审计；不把每只证券作为独立组织。",
            "官网、注册地、总部、控制关系与实际金融交易不能从交易代码推出，均待独立核验。",
            "不保证覆盖所有美国上市主体或所有交易所；未知交易所代码按源代码保留，OTC 不属于本目录范围。",
            "XOM 的源名称为 ExxonMobil Holdings Corporation，与既有 Exxon Mobil Corporation 档案不同，暂不自动合并。",
        ],
        "raw_count": raw_count, "included_count": len(records), "excluded_count": len(excluded),
        "included_security_count": included_securities, "collapsed_security_count": included_securities - len(records),
        "exclusion_counts": dict(sorted(reasons.items())), "raw_file": files[0]["path"], "raw_files": files,
        "sha256": files[0]["sha256"], "combined_manifest_sha256": combined.hexdigest(),
        "excluded_audit_file": "data/sources/sec/nasdaq_exclusions.json",
        "identity_conflicts": [{"ticker": "XOM", "catalog_name": "ExxonMobil Holdings Corporation", "curated_id": "exxonmobil", "curated_name": "Exxon Mobil Corporation", "resolution": "not_merged_pending_review"}],
        "curated_matches": sum("curated_id" in record for record in records),
    }
    return {"metadata": metadata, "records": records}, excluded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "data/sources/sec")
    parser.add_argument("--output", type=Path, default=ROOT / "data/catalogs/nasdaq.json")
    parser.add_argument("--retrieved-at", required=True, help="Actual download date YYYY-MM-DD; does not imply fact verification")
    parser.add_argument("--download", action="store_true", help="Explicitly refresh the two public Nasdaq files (never used during offline build)")
    args = parser.parse_args()
    if args.download:
        args.source_dir.mkdir(parents=True, exist_ok=True)
        for filename, url in URLS.items():
            request = urllib.request.Request(url, headers={"User-Agent": "InstitutionalAtlas/0.3 (https://github.com/permutation248/institutional-atlas)"})
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read()
            temporary = args.source_dir / (filename + ".download")
            temporary.write_bytes(payload)
            # Validate before replacing a saved good snapshot.
            if b"Security Name|" not in payload[:300] or b"File Creation Time:" not in payload[-200:]:
                temporary.unlink()
                raise ValueError(f"Download is not a Nasdaq directory: {filename}")
            temporary.replace(args.source_dir / filename)
    catalog, excluded = build_catalog(args.source_dir, args.retrieved_at)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    (args.source_dir / "nasdaq_exclusions.json").write_text(json.dumps(excluded, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(catalog["metadata"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
