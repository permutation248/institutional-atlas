#!/usr/bin/env python3
"""Validate Markdown facts and build an offline explorer; this does not verify websites."""
from __future__ import annotations

import argparse
import copy
import ipaddress
import json
import math
import re
import sys
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "entities"
OUT = ROOT / "dist"
ALLOWED_TYPES = {"PART_OF", "REPORTS_TO", "CONTROLLED_BY", "FUNCTION_DELEGATED_BY", "FINANCIALLY_DEPENDENT_ON"}
HIERARCHY_TYPES = {"PART_OF", "REPORTS_TO", "CONTROLLED_BY"}
DOMAINS = {"government", "finance", "enterprise", "university"}
CATEGORIES = {
    "government_system", "government_branch", "legislative_body", "court",
    "executive_department", "executive_agency", "independent_agency",
    "university_system", "university_campus", "enterprise_group", "company_subsidiary",
    "financial_group", "regulated_bank", "government_unit", "nonprofit",
    "public_corporation", "research_institute",
}
WEBSITE_TYPES = {"official", "shared_group_site", "government_portal", "group_customer_site", "business_site"}
VERIFICATION_STATUSES = {"verified", "partial", "unverified", "needs_review", "conflict"}
LEADER_STATUSES = {"confirmed", "serving", "acting", "performing_duties", "vacant", "interim", "ex_officio", "unknown"}
MONEY_METRICS = {"authorized_budget", "appropriation", "obligation", "outlay", "contract_value", "recognized_revenue", "net_income", "cash_flow"}
DATE_FIELDS = {"verified_at", "research_reviewed_at", "as_of", "valid_from", "valid_to", "observed_at", "source_published_at", "source_date", "reviewed_at", "published_at", "retrieved_at"}
ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


class UniqueKeyLoader(yaml.SafeLoader):
    """Do not silently replace facts when frontmatter contains duplicate YAML keys."""


def _unique_mapping(loader, node, deep=False):
    loader.flatten_mapping(node)
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise ValueError("YAML mapping keys must be strings")
        if key in result:
            raise ValueError(f"duplicate YAML key {key!r}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping)


def valid_url(value):
    """Accept absolute HTTPS URLs without credentials, whitespace or invalid hosts/ports."""
    if not isinstance(value, str) or not value or any(c.isspace() or ord(c) < 32 or ord(c) == 127 for c in value):
        return False
    if "\\" in value or any(c in value for c in '<>"`{}|^') or re.search(r"%(?![0-9A-Fa-f]{2})", value):
        return False
    try:
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username is not None or parsed.password is not None:
            return False
        if parsed.netloc.endswith(":") or (parsed.port is not None and not 1 <= parsed.port <= 65535):
            return False
        host = parsed.hostname.rstrip(".")
        try:
            ipaddress.ip_address(host)
            return True
        except ValueError:
            host = host.encode("idna").decode("ascii")
            return len(host) <= 253 and "." in host and all(
                re.fullmatch(r"[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?", label)
                for label in host.split(".")
            )
    except (ValueError, UnicodeError):
        return False


def _json_values(value, active=None):
    """Normalize YAML dates and reject cycles, non-JSON types and non-finite numbers."""
    active = set() if active is None else active
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("numbers must be finite")
        return value
    if isinstance(value, (list, dict)):
        if id(value) in active:
            raise ValueError("recursive YAML aliases are not supported")
        active.add(id(value))
        if isinstance(value, list):
            result = [_json_values(item, active) for item in value]
        else:
            if any(not isinstance(key, str) for key in value):
                raise ValueError("mapping keys must be strings")
            result = {key: _json_values(item, active) for key, item in value.items()}
        active.remove(id(value))
        return result
    raise ValueError(f"unsupported YAML value type: {type(value).__name__}")


def read_frontmatter(file, root=ROOT):
    lines = file.read_text(encoding="utf-8").split("\n")
    if not lines or lines[0] != "---":
        raise ValueError("frontmatter required")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError("closing YAML delimiter missing") from exc
    data = _json_values(yaml.load("\n".join(lines[1:end]), Loader=UniqueKeyLoader))
    if not isinstance(data, dict):
        raise ValueError("YAML must be mapping")
    try:
        data["__file__"] = str(file.relative_to(root))
    except ValueError:
        data["__file__"] = str(file)
    return data


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string")


def _list(value, field):
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")


def _mapping(value, field):
    if not isinstance(value, dict):
        raise ValueError(f"{field} must be a mapping")


def _url(value, field):
    if not valid_url(value):
        raise ValueError(f"{field} must be an absolute HTTPS URL with a valid host and no credentials")


def _date(value, field):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"{field} must be an ISO date (YYYY-MM-DD)")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be a real calendar date") from exc


def _dates(value, path=""):
    if isinstance(value, dict):
        for key, item in value.items():
            field = f"{path}.{key}" if path else key
            if key in DATE_FIELDS and item is not None:
                _date(item, field)
            _dates(item, field)
        if value.get("valid_from") and value.get("valid_to") and value["valid_from"] > value["valid_to"]:
            raise ValueError(f"{path}: valid_to must not precede valid_from")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _dates(item, f"{path}[{index}]")


def _number(value, field, nonnegative=False):
    if type(value) not in (int, float) or (isinstance(value, float) and not math.isfinite(value)):
        raise ValueError(f"{field} must be a finite number, not a boolean or numeric string")
    if nonnegative and value < 0:
        raise ValueError(f"{field} must be nonnegative")


def _financial_dependency(edge, field):
    """Require comparable, evidenced operating shares above 50% in consecutive years."""
    periods = edge.get("periods")
    _list(periods, f"{field}.periods")
    if len(periods) < 2:
        raise ValueError(f"{field} needs at least two documented consecutive years")
    if "funding_share" in edge:
        _number(edge["funding_share"], f"{field}.funding_share")
        if not .5 < edge["funding_share"] <= 1:
            raise ValueError(f"{field}.funding_share must be > 0.5 and <= 1")
    years, bases = [], set()
    for index, period in enumerate(periods):
        prefix = f"{field}.periods[{index}]"
        _mapping(period, prefix)
        year = period.get("year")
        if type(year) is not int or not 1000 <= year <= 9999:
            raise ValueError(f"{prefix}.year must be a four-digit integer")
        years.append(year)
        for key in ("funding_share", "numerator", "denominator"):
            _number(period.get(key), f"{prefix}.{key}", nonnegative=True)
        share, numerator, denominator = (period[key] for key in ("funding_share", "numerator", "denominator"))
        if not .5 < share <= 1 or denominator <= 0 or numerator > denominator or not math.isclose(numerator / denominator, share, rel_tol=1e-6):
            raise ValueError(f"{prefix} must document a consistent funding share > 0.5 and <= 1")
        for key in ("currency", "scope"):
            _text(period.get(key), f"{prefix}.{key}")
        if not re.fullmatch(r"[A-Z]{3}", period["currency"]):
            raise ValueError(f"{prefix}.currency must be a three-letter currency code")
        bases.add((period["currency"], period["scope"]))
        _url(period.get("evidence_url"), f"{prefix}.evidence_url")
    ordered = sorted(years)
    if len(set(years)) != len(years) or any(b != a + 1 for a, b in zip(ordered, ordered[1:])) or len(bases) != 1:
        raise ValueError(f"{field}.periods must use consecutive distinct years and comparable currency/scope")


def validate_entity(data, file):
    for field in ("id", "name", "name_zh", "category", "jurisdiction", "domain", "official_url", "website_type", "function", "verified_at", "verification_status"):
        _text(data.get(field), field)
    if not ID_PATTERN.fullmatch(data["id"]) or file.stem != data["id"]:
        raise ValueError("id must be a lowercase hyphenated identifier matching the Markdown filename")
    if data["domain"] not in DOMAINS or file.parent.name != data["domain"]:
        raise ValueError("domain must be supported and match its source directory")
    if data["category"] not in CATEGORIES:
        raise ValueError("unsupported category; extend the schema and UI deliberately")
    if data["website_type"] not in WEBSITE_TYPES:
        raise ValueError("unsupported website_type; shared websites must be labeled")
    if data["verification_status"] not in VERIFICATION_STATUSES:
        raise ValueError("unsupported verification_status")
    _date(data["verified_at"], "verified_at")
    _dates(data)
    _url(data["official_url"], "official_url")
    for field in ("sources", "parents", "publications", "financial_profile"):
        _list(data.get(field), field)
    if not data["sources"]:
        raise ValueError("every node must cite a source")
    for index, source in enumerate(data["sources"]):
        _mapping(source, f"sources[{index}]")
        _url(source.get("url"), f"sources[{index}].url")
        if "description" in source:
            _text(source["description"], f"sources[{index}].description")
    for index, publication in enumerate(data["publications"]):
        _mapping(publication, f"publications[{index}]")
        _text(publication.get("label"), f"publications[{index}].label")
        _url(publication.get("url"), f"publications[{index}].url")
    if "aliases" in data:
        _list(data["aliases"], "aliases")
        for alias in data["aliases"]:
            _text(alias, "aliases[]")
    leader = data.get("leader")
    if leader is not None:
        _mapping(leader, "leader")
        _text(leader.get("title"), "leader.title")
        if not isinstance(leader.get("status"), str) or leader["status"] not in LEADER_STATUSES:
            raise ValueError("leader.status must explicitly describe the appointment")
        if leader["status"] == "vacant":
            if leader.get("name") is not None:
                raise ValueError("a vacant position must have name: null")
        else:
            _text(leader.get("name"), "leader.name")
        _date(leader.get("as_of"), "leader.as_of")
        _url(leader.get("evidence_url"), "leader.evidence_url")
    count = data.get("employee_count")
    if count is not None:
        _mapping(count, "employee_count")
        _number(count.get("value"), "employee_count.value", nonnegative=True)
        if type(count["value"]) is not int:
            raise ValueError("employee_count.value must be an integer")
        for field in ("unit", "period"):
            _text(count.get(field), f"employee_count.{field}")
        _url(count.get("evidence_url"), "employee_count.evidence_url")
        if "approximate" in count and type(count["approximate"]) is not bool:
            raise ValueError("employee_count.approximate must be a boolean")
    for index, money in enumerate(data["financial_profile"]):
        prefix = f"financial_profile[{index}]"
        _mapping(money, prefix)
        metric = money.get("metric", money.get("type"))
        if not isinstance(metric, str) or metric not in MONEY_METRICS:
            raise ValueError(f"{prefix}.metric must distinguish the financial accounting basis")
        _number(money.get("value"), f"{prefix}.value")
        if not isinstance(money.get("currency"), str) or not re.fullmatch(r"[A-Z]{3}", money["currency"]):
            raise ValueError(f"{prefix}.currency must be a three-letter currency code")
        if "fiscal_year" in money:
            if type(money["fiscal_year"]) is not int or not 1000 <= money["fiscal_year"] <= 9999:
                raise ValueError(f"{prefix}.fiscal_year must be a four-digit integer")
        else:
            _text(money.get("reporting_period"), f"{prefix}.reporting_period")
        _text(money.get("scope", money.get("reporting_scope")), f"{prefix}.scope")
        _url(money.get("source_url"), f"{prefix}.source_url")
        _date(money.get("source_date", money.get("reviewed_at")), f"{prefix}.source_date/reviewed_at")
    seen = set()
    for index, parent in enumerate(data["parents"]):
        prefix = f"parents[{index}]"
        _mapping(parent, prefix)
        _text(parent.get("parent_id"), f"{prefix}.parent_id")
        if not ID_PATTERN.fullmatch(parent["parent_id"]):
            raise ValueError(f"{prefix}.parent_id must be a stable identifier")
        if not isinstance(parent.get("type"), str) or parent["type"] not in ALLOWED_TYPES:
            raise ValueError(f"{prefix}: unknown relation type")
        _url(parent.get("evidence_url"), f"{prefix}.evidence_url")
        if parent["parent_id"] == data["id"]:
            raise ValueError("self reference")
        key = (parent["parent_id"], parent["type"])
        if key in seen:
            raise ValueError(f"duplicate relation {key}; consolidate its evidence in one record")
        seen.add(key)
        if "child_id" in parent:
            raise ValueError("child_id is derived from the source node and cannot be overridden")
        if "note" in parent and not isinstance(parent["note"], str):
            raise ValueError(f"{prefix}.note must be a string")
        if parent["type"] == "FINANCIALLY_DEPENDENT_ON":
            _financial_dependency(parent, prefix)
        if parent["type"] == "FUNCTION_DELEGATED_BY":
            _text(parent.get("scope", parent.get("note")), f"{prefix}.scope/note")


def load_data(data_dir=None, root=None):
    data_dir, root = Path(data_dir or DATA), Path(root or ROOT)
    entities, errors = {}, []
    for file in sorted(data_dir.glob("*/*.md")):
        try:
            record = read_frontmatter(file, root)
            validate_entity(record, file)
            if record["id"] in entities:
                raise ValueError(f"duplicate id {record['id']}")
            entities[record["id"]] = record
        except (ValueError, yaml.YAMLError, OSError) as exc:
            errors.append(f"{file}: {exc}")
    for node in entities.values():
        for edge in node["parents"]:
            if edge["parent_id"] not in entities:
                errors.append(f"{node['id']}: missing parent {edge['parent_id']}")
    if not entities:
        errors.append("No valid Markdown records found")
    # Funding can be reciprocal; hierarchy, control and reporting must remain acyclic.
    color = {}
    def visit(node, stack):
        if color.get(node) == 1:
            errors.append("Relation cycle: " + " -> ".join(stack + [node]))
            return
        if color.get(node) == 2:
            return
        color[node] = 1
        for edge in entities[node]["parents"]:
            if edge["type"] in HIERARCHY_TYPES and edge["parent_id"] in entities:
                visit(edge["parent_id"], stack + [node])
        color[node] = 2
    for node in entities:
        visit(node, [])
    if errors:
        raise ValueError("\n".join(errors))
    # Keep all relation metadata, including temporal and quantified dependency evidence.
    edges = [{**copy.deepcopy(edge), "child_id": node["id"], "note": edge.get("note", "")}
             for node in entities.values() for edge in node["parents"]]
    return {
        "metadata": {
            "snapshot_date": max(node["verified_at"] for node in entities.values()),
            "scope": "Selected U.S. institutions; not a comprehensive directory",
            "source_type": "local Markdown records; schema validation only",
            "network_verification_performed": False,
            "total_entities": len(entities), "total_edges": len(edges),
            "verification_status_counts": dict(sorted(Counter(node["verification_status"] for node in entities.values()).items())),
        },
        "entities": list(entities.values()), "edges": edges,
    }


def coverage_report(graph):
    """Describe recorded coverage without treating source declarations as fresh verification."""
    nodes = graph["entities"]
    by_id = {node["id"]: node for node in nodes}
    def depth(node_id):
        parents = [edge["parent_id"] for edge in by_id[node_id]["parents"] if edge["type"] in HIERARCHY_TYPES]
        return 0 if not parents else 1 + max(depth(parent) for parent in parents)
    def summarize(records):
        total = len(records)
        def field_coverage(predicate):
            missing = sorted(node["id"] for node in records if not predicate(node))
            return {"recorded": total - len(missing), "total": total, "missing_ids": missing}
        reviewed = [node for node in records if node.get("research_reviewed_at")]
        return {
            "total_entities": total,
            "source_declared_status_counts": dict(sorted(Counter(node["verification_status"] for node in records).items())),
            "research_reviewed_entities": len(reviewed),
            "inherited_entities": total - len(reviewed),
            "research_reviewed_dates": dict(sorted(Counter(node["research_reviewed_at"] for node in reviewed).items())),
            "official_website": field_coverage(lambda node: bool(node.get("official_url"))),
            "source_links": field_coverage(lambda node: bool(node.get("sources"))),
            "leader": field_coverage(lambda node: node.get("leader") is not None),
            "employee_count": field_coverage(lambda node: node.get("employee_count") is not None),
            "financial_profile": field_coverage(lambda node: bool(node.get("financial_profile"))),
            "publications": field_coverage(lambda node: bool(node.get("publications"))),
            "max_recorded_hierarchy_depth": max((depth(node["id"]) for node in records), default=0),
        }
    urls = [node["official_url"] for node in nodes]
    urls += [source["url"] for node in nodes for source in node["sources"]]
    urls += [edge["evidence_url"] for edge in graph["edges"]]
    return {
        "schema_version": 1,
        "snapshot_date": graph["metadata"]["snapshot_date"],
        "network_verification_performed": False,
        "interpretation": "Counts describe local records. verification_status and research_reviewed_at are author declarations, not checks performed by this build. Field presence does not establish current accuracy or complete coverage.",
        "total_edges": len(graph["edges"]),
        "overall": summarize(nodes),
        "by_domain": {domain: summarize([node for node in nodes if node["domain"] == domain]) for domain in sorted(DOMAINS)},
        "source_hosts": sorted({urlsplit(url).hostname for url in urls}),
    }


def embedded_json(data):
    result = json.dumps(data, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    for char, escaped in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026"), ("\u2028", "\\u2028"), ("\u2029", "\\u2029")):
        result = result.replace(char, escaped)
    return result


def render_html(graph, web_dir):
    html = (web_dir / "template.html").read_text(encoding="utf-8")
    replacements = {
        "/*__INLINE_CSS__*/": (web_dir / "style.css").read_text(encoding="utf-8"),
        "/*__INLINE_JS__*/": (web_dir / "app.js").read_text(encoding="utf-8"),
        "/*__EMBEDDED_DATA__*/": embedded_json(graph),
    }
    for marker in replacements:
        if html.count(marker) != 1:
            raise ValueError(f"template must contain exactly one {marker}")
    # A single pass cannot interpret marker-like text in source facts or assets as a template.
    return re.sub("|".join(re.escape(marker) for marker in replacements), lambda match: replacements[match.group()], html)


def build(data_dir=None, output_dir=None, web_dir=None, root=None):
    graph = load_data(data_dir, root)
    output_dir, web_dir = Path(output_dir or OUT), Path(web_dir or ROOT / "web")
    outputs = {
        "atlas.json": json.dumps(graph, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        "coverage.json": json.dumps(coverage_report(graph), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        "index.html": render_html(graph, web_dir),
    }
    # Validate and render everything before touching previously built output.
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        temporary = output_dir / f".{name}.tmp"
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(output_dir / name)
    return graph


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=DATA)
    parser.add_argument("--out-dir", type=Path, default=OUT)
    parser.add_argument("--web-dir", type=Path, default=ROOT / "web")
    args = parser.parse_args()
    graph = build(args.data_dir, args.out_dir, args.web_dir)
    groups = Counter(node["domain"] for node in graph["entities"])
    print(f"Built {len(graph['entities'])} entities, {len(graph['edges'])} sourced edges: {dict(groups)}")
    print("Schema validation passed; source websites were not re-verified by this command.")
    print(f"Offline explorer: {args.out_dir / 'index.html'}")
    print(f"Recorded coverage: {args.out_dir / 'coverage.json'}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as exc:
        print("Validation failed:\n" + str(exc), file=sys.stderr)
        raise SystemExit(1)
