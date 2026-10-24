#!/usr/bin/env python3
"""Rebuild the complete government-directory snapshot, without inventing hierarchy.

Default is offline. --download refreshes official public sources and the retrieval
manifest before rebuilding. Federal Register includes historical entities; USA.gov
also includes instrumentalities, government-sponsored enterprises and aggregates.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import time
from collections import defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/sources/agencies"
FR_URL = "https://www.federalregister.gov/api/v1/agencies.json"
USA_URL = "https://www.usa.gov/agency-index"

# These labels denote directory collections, rather than individual organizations.
AGGREGATES = {"Bankruptcy Courts", "Federal Executive Boards", "Federal Courts", "Military Academies", "U.S. Courts of Appeals", "U.S. District Courts", "State and Local Governments", "Circuit Courts of Appeal", "Unified Combatant Commands", "National Laboratories", "White House"}
PROGRAMS = {"Fulbright Program", "National Flood Insurance Program", "Indoor Air Quality", "Elder Justice Initiative"}
# Identity-only crosswalks. They never imply present-day administrative control.
CURATED_FR = {
    3: "us-courts-administration", 5: "us-ahrq", 7: "us-atsdr", 12: "us-agriculture",
    18: "us-ttb", 42: "us-census", 44: "us-cdc", 45: "us-cms", 49: "us-acf",
    54: "us-commerce", 77: "us-cftc", 80: "us-occ", 81: "us-cbo", 103: "us-defense",
    118: "us-bea", 120: "us-eda", 126: "us-education", 136: "us-energy", 143: "us-bep",
    145: "us-epa", 161: "us-fcc", 164: "us-fdic", 188: "us-federal-reserve-system",
    192: "us-ftc", 194: "us-fincen", 196: "us-fiscal", 199: "us-fda", 210: "us-gsa",
    213: "us-gao", 221: "us-hhs", 222: "us-hrsa", 227: "us-dhs", 228: "us-hud",
    237: "us-ihs", 241: "us-bis", 253: "us-interior", 254: "us-irs", 261: "us-ita",
    268: "us-justice", 271: "us-labor", 280: "us-omb", 301: "us-nasa", 352: "us-nist",
    353: "us-nih", 361: "us-noaa", 366: "us-nsf", 372: "us-ntis", 402: "us-uspto",
    466: "us-sec", 468: "us-sba", 476: "us-state", 479: "us-samhsa", 492: "us-transportation",
    497: "us-treasury", 502: "us-house", 513: "us-mint", 520: "us-va", 573: "us-cfpb",
    587: "us-acl", 615: "us-aspr", 622: "us-treasury-oig",
}
# Different displayed names, reviewed against the supplied descriptions / URLs.
USA_FR_ALIASES = {
    "Administration for Children and Families": 49, "Administration for Community Living": 587,
    "Comptroller of the Currency, Office of": 80,
    "Army Corps of Engineers": 142, "Copyright Office": 87, "Commission on Civil Rights": 52,
    "Federal Register": 186, "Udall Foundation": 296, "Trade Representative": 491,
    "Archives, National Archives and Records Administration": 304,
    "Federal Law Enforcement Training Centers": 177, "Agriculture Library": 302,
    "Chemical Safety Board": 47, "Director of National Intelligence, Office of": 354,
    "AmeriCorps": 91, "Ginnie Mae": 216, "Congress—U.S. House of Representatives": 502,
    "AbilityOne Commission": 74, "Access Board": 28, "Agency for Global Media": 608,
    "Bureau of Alcohol and Tobacco Tax and Trade": 18, "Bureau of Consumer Financial Protection": 573,
    "Bureau of the Census": 42, "Bureau of Prisons": 437, "Federal Reserve": 188,
    "National Railroad Passenger Corporation": 365, "Amtrak": 365,
    "U.S. Agency for International Development": 6,
}
CURATED_USA = {"1430": "us-senate"}


def plain(value):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", value or "")).split())


def name_key(value):
    """Match the exact name-token multiset, allowing FR's inverted word order."""
    value = re.sub(r"\([^)]*\)", "", value.lower())
    value = value.replace("united states", "").replace("u.s.", "").replace("&", " and ")
    return " ".join(sorted(t for t in re.findall(r"[a-z0-9]+", value) if t not in {"the", "of"}))


def https_url(value):
    """Preserve HTTPS only: never claim an untested HTTP→HTTPS upgrade worked."""
    if not isinstance(value, str) or any(c.isspace() for c in value):
        return None
    try:
        p = urlsplit(value)
        return value if p.scheme == "https" and p.hostname and "." in p.hostname and not p.username and not p.password else None
    except ValueError:
        return None


def parse_usagov(text):
    records = []
    for block in re.split(r'<h2 class="usa-accordion__heading">', text)[1:]:
        button = re.search(r'<button\b[^>]*data-agency-name="[^"]+"[^>]*>(.*?)</button>', block, re.S)
        node = re.search(r'data-node-id="(\d+)"', block)
        website = re.search(r'class="field--name-field-website"[^>]*>\s*<a[^>]*href="([^"]+)"', block)
        detail = re.search(r'class="field--name-field-more-information".*?<a[^>]*href="([^"]+)"', block, re.S)
        desc = re.search(r'class="usa-accordion__content[^>]+>\s*<p>(.*?)</p>', block, re.S)
        if not button or not node:
            raise ValueError("USA.gov directory markup changed: missing agency identity")
        records.append({"id": node.group(1), "name": plain(button.group(1)),
                        "agency_url": html.unescape(website.group(1)) if website else None,
                        "url": urljoin(USA_URL, html.unescape(detail.group(1))) if detail else USA_URL + "#" + re.search(r'aria-controls="([^"]+)"', block).group(1),
                        "description": plain(desc.group(1)) if desc else None})
    if not records:
        raise ValueError("USA.gov directory page contains no agency cards")
    return records


def download_sources(source_dir=SOURCE):
    source_dir.mkdir(parents=True, exist_ok=True)
    def fetch(url, filename):
        time.sleep(.4)
        data = urlopen(Request(url, headers={"User-Agent": "InstitutionalAtlas/0.3 public-directory-research"}), timeout=60).read()
        (source_dir / filename).write_bytes(data)
        return data
    fr = fetch(FR_URL, "federal-register-agencies.json")
    if not isinstance(json.loads(fr), list):
        raise ValueError("Federal Register API did not return an agency array")
    first = fetch(USA_URL, "usagov-a.html").decode("utf-8")
    pages = sorted(set(re.findall(r'href="(/agency-index/[a-z])#', first)))
    if len(pages) < 20:
        raise ValueError("USA.gov letter index changed; refusing a partial refresh")
    for path in pages:
        parse_usagov(fetch("https://www.usa.gov" + path, "usagov-" + path[-1] + ".html").decode("utf-8"))
    files = [source_dir / "federal-register-agencies.json"] + sorted(source_dir.glob("usagov-?.html"))
    manifest = {"retrieved_at": date.today().isoformat(), "sources": [
        {"path": str(p.relative_to(ROOT)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
    (source_dir / "retrieval.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def curated_name_index(entities_dir):
    index = defaultdict(list)
    for path in sorted(entities_dir.glob("*/*.md")):
        d = yaml.safe_load(path.read_text(encoding="utf-8").split("---", 2)[1])
        if d.get("domain") in {"government", "finance"}:
            index[name_key(d["name"])].append(d["id"])
    return index


def build_catalog(source_dir=SOURCE, entities_dir=ROOT / "data/entities"):
    manifest = json.loads((source_dir / "retrieval.json").read_text())
    raw = json.loads((source_dir / "federal-register-agencies.json").read_text())
    if not isinstance(raw, list) or not raw:
        raise ValueError("Federal Register source must be a nonempty list")
    seen, records, name_index = set(), [], defaultdict(list)
    curated = curated_name_index(entities_dir)
    for agency in raw:
        aid = agency["id"]
        if type(aid) is not int or aid in seen or not agency.get("name"):
            raise ValueError("duplicate or invalid Federal Register agency ID")
        seen.add(aid)
        record = {"id": f"fr-{aid}", "name": agency["name"], "name_zh": None,
                  "domain": "government", "category": "government_unit", "jurisdiction": "US",
                  "official_url": https_url(agency.get("agency_url")), "registry_url": agency["url"],
                  "aliases": [agency["short_name"]] if agency.get("short_name") and agency["short_name"] != agency["name"] else [],
                  "identifiers": {"federal_register_id": str(aid)}, "catalog_source": "agencies",
                  "record_kind": "directory", "location": None,
                  "source_fields": {k: agency.get(k) for k in ("parent_id", "child_ids", "slug", "description", "agency_url")}}
        record["source_fields"]["current_status"] = "not_verified_includes_historical"
        if aid in CURATED_FR:
            record["curated_id"] = CURATED_FR[aid]
        records.append(record)
        name_index[name_key(agency["name"])].append(record)
    by_fr = {int(r["identifiers"]["federal_register_id"]): r for r in records}
    us_seen, us_count, matched, excluded = set(), 0, 0, []
    for path in sorted(source_dir.glob("usagov-?.html")):
        for agency in parse_usagov(path.read_text(encoding="utf-8")):
            if agency["id"] in us_seen:
                continue
            us_seen.add(agency["id"])
            us_count += 1
            name = re.sub(r"\s*\([^)]*\)\s*$", "", agency["name"])
            if name in AGGREGATES or name in PROGRAMS:
                excluded.append({"name": agency["name"], "registry_url": agency["url"], "reason": "collection_place_or_program_not_single_organization"})
                continue
            candidates = name_index.get(name_key(name), [])
            if name in USA_FR_ALIASES:
                candidates = [by_fr[USA_FR_ALIASES[name]]]
            if len(candidates) == 1:
                r = candidates[0]
                r["identifiers"]["usagov_node_id"] = agency["id"]
                r["source_fields"]["usagov"] = agency
                r["source_fields"]["current_status"] = "listed_in_usagov_snapshot_not_independently_verified"
                r["aliases"] = sorted(set(r["aliases"] + [agency["name"]]))
                if not r["official_url"]:
                    r["official_url"] = https_url(agency.get("agency_url"))
                matched += 1
            else:
                r = {"id": f"usagov-{agency['id']}", "name": agency["name"], "name_zh": None,
                     "domain": "government", "category": "government_unit", "jurisdiction": "US",
                     "official_url": https_url(agency.get("agency_url")), "registry_url": agency["url"], "aliases": [],
                     "identifiers": {"usagov_node_id": agency["id"]}, "catalog_source": "agencies",
                     "record_kind": "directory", "location": None,
                     "source_fields": {"usagov": agency, "current_status": "listed_in_usagov_snapshot_not_independently_verified"}}
                records.append(r)
            if "curated_id" not in r and len(curated.get(name_key(name), [])) == 1:
                r["curated_id"] = curated[name_key(name)][0]
            if agency['id'] in CURATED_USA:
                r['curated_id'] = CURATED_USA[agency['id']]
    # Each imported row represents one identity. Refuse accidental two-row curated merges.
    targets = [r["curated_id"] for r in records if r.get("curated_id")]
    if len(targets) != len(set(targets)):
        raise ValueError("ambiguous curated identity crosswalk: " + str([(r['id'], r['name'], r.get('curated_id')) for r in records if r.get('curated_id') and targets.count(r['curated_id']) > 1]))
    files = manifest["sources"]
    for item in files:
        path = ROOT / item["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise ValueError("source snapshot hash mismatch: " + item["path"])
    metadata = {
        "id": "agencies", "title": "美国联邦与公共机构 · FR + USA.gov 官方名录",
        "source_url": FR_URL, "retrieved_at": manifest["retrieved_at"], "source_period": manifest["retrieved_at"] + " retrieval snapshot",
        "scope": "Federal Register 全部机构索引（含历史记录），并合并 USA.gov A–Z 全部字母分页；包括公共机构、政府公司和政府支持企业，不是全部现存联邦/州/地方机构。",
        "license": "U.S. federal government public directory data; third-party marks excluded from derived catalog.",
        "coverage_notes": ["FR 父级字段保留为来源资料，不据此生成现行控制或行政隶属关系。", "USA.gov 上架状态不等于独立核验的存续状态；没有将历史机构判成当前机构。", "无坐标、负责人、治理或资金事实时保留未知。", "HTTP 官网原样保留在来源字段；未测试 HTTPS 的网址不冒充已验证官网。", "同名/倒装名称按唯一词项匹配，明确别名单独交叉表；来源本身的历史更名可能仍需复核。"],
        "raw_count": len(raw) + us_count, "included_count": len(records), "excluded_count": len(excluded),
        "duplicate_count": matched, "federal_register_count": len(raw), "usagov_count": us_count,
        "usagov_pages": len(list(source_dir.glob("usagov-?.html"))), "excluded_records": excluded,
        "curated_crosswalk_count": len(targets), "raw_file": "data/sources/agencies/federal-register-agencies.json",
        "sha256": hashlib.sha256((source_dir / "federal-register-agencies.json").read_bytes()).hexdigest(),
        "raw_files": files,
    }
    return {"metadata": metadata, "records": sorted(records, key=lambda r: r["id"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true", help="refresh public official snapshots before importing")
    args = parser.parse_args()
    if args.download:
        download_sources()
    catalog = build_catalog()
    output = ROOT / "data/catalogs/agencies.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(catalog, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({k: catalog["metadata"][k] for k in ("included_count", "raw_count", "duplicate_count", "excluded_count", "curated_crosswalk_count")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
