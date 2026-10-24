#!/usr/bin/env python3
"""Validate Markdown facts and build an offline explorer; this does not verify websites."""
from __future__ import annotations

import argparse
import copy
import hashlib
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

from catalogs import merge_catalogs
from catalog_identity import merge_catalog_identities

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
DATE_FIELDS = {"verified_at", "research_reviewed_at", "as_of", "valid_from", "valid_to", "observed_at", "source_published_at", "source_date", "reviewed_at", "published_at", "retrieved_at", "scheduled_for", "date"}
ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
SECTORS = [
    {"id": "households", "name_zh": "家庭与个人", "description": "用于解释消费、税收、储蓄和劳动收入的经济部门；不是单一组织。"},
    {"id": "businesses", "name_zh": "企业部门", "description": "用于解释生产、投资与企业税收的集合；不表示企业共享上级。"},
    {"id": "investors", "name_zh": "投资者", "description": "购买证券或提供风险资本的参与者集合；不是单一机构。"},
    {"id": "banks", "name_zh": "银行体系", "description": "用于解释存款、贷款与支付的金融中介集合；不表示政府所有权。"},
    {"id": "universities", "name_zh": "大学部门", "description": "用于解释学费、科研资助与教育支出的集合；不是行政隶属关系。"},
    {"id": "capital-markets", "name_zh": "资本市场", "description": "证券发行与交易的制度性市场；不是一个法人或管理机关。"},
    {"id": "federal-budget", "name_zh": "联邦预算体系", "description": "国会授权与拨款、行政执行和财政结算的概念性枢纽；不是独立组织。"},
]


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
    for field in ("mission", "ecosystem_role"):
        if data.get(field) is not None:
            _text(data[field], field)
    location = data.get("location")
    if location is not None:
        _mapping(location, "location")
        for key, lower, upper in (("lat", -90, 90), ("lon", -180, 180)):
            _number(location.get(key), f"location.{key}")
            if not lower <= location[key] <= upper:
                raise ValueError(f"location.{key} must be between {lower} and {upper}")
        for key in ("city", "state"):
            _text(location.get(key), f"location.{key}")
        if location.get("precision") not in ("city", "campus", "headquarters"):
            raise ValueError("location.precision must distinguish city, campus or headquarters")
        _url(location.get("evidence_url"), "location.evidence_url")
    governance = data.get("governance")
    if governance is not None:
        _mapping(governance, "governance")
        for key in ("apex", "mechanism"):
            _text(governance.get(key), f"governance.{key}")
        _url(governance.get("evidence_url"), "governance.evidence_url")
    funding = data.get("funding_model")
    if funding is not None:
        _mapping(funding, "funding_model")
        _text(funding.get("summary"), "funding_model.summary")
        for key in ("inflows", "outflows"):
            _list(funding.get(key), f"funding_model.{key}")
            for item in funding[key]:
                _text(item, f"funding_model.{key}[]")
        _url(funding.get("evidence_url"), "funding_model.evidence_url")
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


def _record_id(record, file):
    _text(record.get("id"), "id")
    if not ID_PATTERN.fullmatch(record["id"]) or record["id"] != file.stem:
        raise ValueError("id must be a lowercase hyphenated identifier matching the Markdown filename")


def validate_event(record, file, entity_ids):
    _record_id(record, file)
    for key in ("title", "summary", "category", "source_name"):
        _text(record.get(key), key)
    _dates(record)
    _date(record.get("date"), "date")
    _date(record.get("reviewed_at"), "reviewed_at")
    if record["date"] > record["reviewed_at"]:
        raise ValueError("event publication date must not follow reviewed_at; future schedules need a separate field")
    _url(record.get("source_url"), "source_url")
    _list(record.get("entity_ids"), "entity_ids")
    if not record["entity_ids"]:
        raise ValueError("event must reference at least one organization")
    seen = set()
    for entity_id in record["entity_ids"]:
        _text(entity_id, "entity_ids[]")
        if entity_id not in entity_ids:
            raise ValueError(f"event references missing entity {entity_id}")
        if entity_id in seen:
            raise ValueError(f"duplicate event entity reference {entity_id}")
        seen.add(entity_id)


def validate_flow(record, file, endpoint_ids):
    _record_id(record, file)
    for key in ("source_id", "target_id", "label", "kind", "description"):
        _text(record.get(key), key)
    for key in ("source_id", "target_id"):
        if record[key] not in endpoint_ids:
            raise ValueError(f"flow references missing endpoint {record[key]}")
    if record["source_id"] == record["target_id"]:
        raise ValueError("flow cannot reference itself")
    if record.get("basis") != "mechanism":
        raise ValueError("flow basis must be mechanism; quantified transfers need a separate accounting schema")
    if "amount" not in record or record["amount"] is not None:
        raise ValueError("mechanism flow must explicitly have amount: null; it is not a quantified transfer")
    _url(record.get("evidence_url"), "evidence_url")
    _date(record.get("as_of"), "as_of")
    _dates(record)


def load_supplementary(directory, root, validator):
    records, errors = {}, []
    for file in sorted(directory.rglob("*.md")):
        try:
            record = read_frontmatter(file, root)
            validator(record, file)
            if record["id"] in records:
                raise ValueError(f"duplicate id {record['id']}")
            records[record["id"]] = record
        except (ValueError, yaml.YAMLError, OSError) as exc:
            errors.append(f"{file}: {exc}")
    if errors:
        raise ValueError("\n".join(errors))
    return list(records.values())


MAP_REGIONS = {
    "mainland": {"lon": [-125, -66], "lat": [24, 50], "box": [0, 0, 1000, 600]},
    "alaska": {"lon": [-190, -130], "lat": [50, 72], "box": [20, 480, 230, 105]},
    "hawaii": {"lon": [-161, -154], "lat": [18, 23], "box": [285, 490, 130, 85]},
}


def project_location(lon, lat, region="mainland"):
    """Equirectangular map coordinates; Alaska/Hawaii use explicitly labeled insets."""
    config = MAP_REGIONS[region]
    if region == "alaska" and lon > 0:
        lon -= 360  # Join the Aleutian islands across the antimeridian.
    west, east = config["lon"]
    south, north = config["lat"]
    x, y, width, height = config["box"]
    return x + (lon - west) / (east - west) * width, y + (north - lat) / (north - south) * height


def load_geography(directory, root):
    """Decode the vendored Census-derived topology into small, offline SVG paths."""
    descriptor = directory / "us-states.md"
    if not descriptor.exists():
        return None
    metadata = read_frontmatter(descriptor, root)
    for key in ("source_url", "upstream_url"):
        _url(metadata.get(key), key)
    for key in ("license", "dataset", "source_sha256"):
        _text(metadata.get(key), key)
    _date(metadata.get("retrieved_at"), "retrieved_at")
    raw = (directory / "states-10m.topo.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != metadata["source_sha256"]:
        raise ValueError("geography source checksum mismatch; review the source and update its descriptor")
    topology = json.loads(raw)
    scale, translate = topology["transform"]["scale"], topology["transform"]["translate"]
    arcs = []
    for arc in topology["arcs"]:
        x, y, coordinates = 0, 0, []
        for dx, dy in arc:
            x, y = x + dx, y + dy
            coordinates.append((x * scale[0] + translate[0], y * scale[1] + translate[1]))
        arcs.append(coordinates)
    states = []
    for feature in topology["objects"]["states"]["geometries"]:
        state_id = feature["id"]
        if int(state_id) >= 60:  # Territories are outside this version's 50-state + DC scope.
            continue
        region = "alaska" if state_id == "02" else "hawaii" if state_id == "15" else "mainland"
        polygons = [feature["arcs"]] if feature["type"] == "Polygon" else feature["arcs"]
        commands = []
        for polygon in polygons:
            for ring in polygon:
                points = []
                for arc_id in ring:
                    segment = arcs[arc_id] if arc_id >= 0 else list(reversed(arcs[~arc_id]))
                    points.extend(segment if not points else segment[1:])
                projected = [project_location(lon, lat, region) for lon, lat in points]
                if any(not math.isfinite(value) for pair in projected for value in pair):
                    raise ValueError("geography coordinates must be finite")
                if projected:
                    commands.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in projected) + "Z")
        states.append({"id": state_id, "name": feature["properties"]["name"], "region": region, "path": "".join(commands)})
    if len(states) != 51 or len({state["id"] for state in states}) != 51:
        raise ValueError("geography must contain the 50 states and District of Columbia exactly once")
    return {
        "viewBox": "0 0 1000 600", "states": states,
        "source_url": metadata["source_url"], "upstream_url": metadata["upstream_url"],
        "dataset": metadata["dataset"], "license": metadata["license"],
        "retrieved_at": metadata["retrieved_at"], "source_sha256": metadata["source_sha256"],
        "projection": {"type": "equirectangular-with-insets", "regions": copy.deepcopy(MAP_REGIONS)},
        "scope": "50 states and District of Columbia; Alaska and Hawaii are relocated and rescaled insets; U.S. territories omitted",
    }


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
    for node in entities.values():
        node["record_kind"] = "curated"
    curated_count = len(entities)
    catalogs = merge_catalogs(data_dir.parent / "catalogs", entities, root, valid_url)
    identity_links = merge_catalog_identities(entities, root, valid_url, path=data_dir.parent / "catalog-links.json")
    # Keep all relation metadata, including temporal and quantified dependency evidence.
    edges = [{**copy.deepcopy(edge), "child_id": node["id"], "note": edge.get("note", "")}
             for node in entities.values() for edge in node["parents"]]
    data_root = data_dir.parent
    events = load_supplementary(data_root / "events", root, lambda record, file: validate_event(record, file, entities))
    sectors = copy.deepcopy(SECTORS)
    endpoint_ids = set(entities) | {sector["id"] for sector in sectors}
    flows = load_supplementary(data_root / "flows", root, lambda record, file: validate_flow(record, file, endpoint_ids))
    all_ids = list(entities) + [sector["id"] for sector in sectors] + [event["id"] for event in events] + [flow["id"] for flow in flows]
    duplicates = [record_id for record_id, count in Counter(all_ids).items() if count > 1]
    if duplicates:
        raise ValueError("duplicate identifiers across entities, sectors, events or flows: " + ", ".join(sorted(duplicates)))
    flow_keys = [(flow["source_id"], flow["target_id"], flow["kind"], flow["label"]) for flow in flows]
    if len(set(flow_keys)) != len(flow_keys):
        raise ValueError("duplicate flow mechanism; consolidate its evidence into one record")
    events.sort(key=lambda event: (event["date"], event["id"]), reverse=True)
    geography = load_geography(data_root / "geography", root)
    snapshot_dates = [node["verified_at"] for node in entities.values() if node.get("verified_at")]
    snapshot_dates += [catalog["retrieved_at"] for catalog in catalogs]
    snapshot_dates += [node["research_reviewed_at"] for node in entities.values() if node.get("research_reviewed_at")]
    snapshot_dates += [event["reviewed_at"] for event in events] + [flow["as_of"] for flow in flows]
    return {
        "metadata": {
            "snapshot_date": max(snapshot_dates),
            "scope": "Official bulk directories plus researched institutional dossiers; see catalog scopes and exclusions",
            "curated_entities": curated_count, "directory_entities": len(entities) - curated_count,
            "catalogs": catalogs, "identity_links": identity_links,
            "source_type": "Markdown dossiers and SHA-256 pinned official directory snapshots; schema validation only",
            "network_verification_performed": False,
            "total_entities": len(entities), "total_edges": len(edges),
            "total_events": len(events), "total_flows": len(flows),
            "geolocated_entities": sum(node.get("location") is not None for node in entities.values()),
            "verification_status_counts": dict(sorted(Counter(node["verification_status"] for node in entities.values()).items())),
        },
        "entities": list(entities.values()), "edges": edges,
        "events": events, "flows": flows, "sectors": sectors, "geography": geography,
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
            "inherited_entities": sum(node.get("record_kind") != "directory" and not node.get("research_reviewed_at") for node in records),
            "directory_entities": sum(node.get("record_kind") == "directory" for node in records),
            "research_reviewed_dates": dict(sorted(Counter(node["research_reviewed_at"] for node in reviewed).items())),
            "official_website": field_coverage(lambda node: bool(node.get("official_url"))),
            "source_links": field_coverage(lambda node: bool(node.get("sources"))),
            "leader": field_coverage(lambda node: node.get("leader") is not None),
            "employee_count": field_coverage(lambda node: node.get("employee_count") is not None),
            "financial_profile": field_coverage(lambda node: bool(node.get("financial_profile"))),
            "publications": field_coverage(lambda node: bool(node.get("publications"))),
            "location": field_coverage(lambda node: node.get("location") is not None),
            "mission": field_coverage(lambda node: bool(node.get("mission"))),
            "ecosystem_role": field_coverage(lambda node: bool(node.get("ecosystem_role"))),
            "governance": field_coverage(lambda node: node.get("governance") is not None),
            "funding_model": field_coverage(lambda node: node.get("funding_model") is not None),
            "max_recorded_hierarchy_depth": max((depth(node["id"]) for node in records), default=0),
        }
    urls = [node["official_url"] for node in nodes if node.get("official_url")]
    urls += [source["url"] for node in nodes for source in node["sources"]]
    urls += [edge["evidence_url"] for edge in graph["edges"]]
    urls += [event["source_url"] for event in graph.get("events", [])]
    urls += [flow["evidence_url"] for flow in graph.get("flows", [])]
    urls += [node[field]["evidence_url"] for node in nodes for field in ("location", "governance", "funding_model") if node.get(field)]
    return {
        "schema_version": 3,
        "catalogs": graph["metadata"].get("catalogs", []),
        "curated_entities": sum(n.get("record_kind") == "curated" for n in nodes),
        "directory_entities": sum(n.get("record_kind") == "directory" for n in nodes),
        "snapshot_date": graph["metadata"]["snapshot_date"],
        "network_verification_performed": False,
        "interpretation": "Counts describe local records. verification_status and research_reviewed_at are author declarations, not checks performed by this build. Field presence does not establish current accuracy or complete coverage.",
        "total_edges": len(graph["edges"]),
        "total_events": len(graph.get("events", [])),
        "total_mechanism_flows": len(graph.get("flows", [])),
        "map_states": len((graph.get("geography") or {}).get("states", [])),
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
    print(f"Context layers: {len(graph['events'])} official events, {len(graph['flows'])} financial mechanisms, {graph['metadata']['geolocated_entities']} mapped institutions")
    print("Schema validation passed; source websites were not re-verified by this command.")
    print(f"Offline explorer: {args.out_dir / 'index.html'}")
    print(f"Recorded coverage: {args.out_dir / 'coverage.json'}")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError) as exc:
        print("Validation failed:\n" + str(exc), file=sys.stderr)
        raise SystemExit(1)
