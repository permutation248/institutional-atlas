"""Apply individually reviewed identity links across official directories.

This module performs no name/website matching or automatic entity resolution.
"""
import copy
from datetime import date
import json
import re


def merge_catalog_identities(entities, root, valid_url, path=None):
    path = path if path is not None else root / "data" / "catalog-links.json"
    if not path.exists():
        return []
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("version") != 1 or not isinstance(document.get("links"), list):
        raise ValueError("Invalid catalog identity links document")
    links = document["links"]
    source_ids, target_ids = set(), set()
    for link in links:
        if not isinstance(link, dict):
            raise ValueError("Invalid catalog identity link")
        source, target = link.get("source_id"), link.get("target_id")
        if any(not isinstance(value, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value) for value in (source, target)) or source == target or source in source_ids:
            raise ValueError("Invalid or duplicate catalog identity source/target")
        source_ids.add(source)
        target_ids.add(target)
    if source_ids & target_ids:
        raise ValueError("Catalog identity chains/cycles require explicit canonical targets")

    # Prepare touched targets only; validation failures never partially mutate
    # the caller's graph or remove an input record.
    updates = {}
    for link in links:
        source_id, target_id = link["source_id"], link["target_id"]
        if source_id not in entities or target_id not in entities:
            raise ValueError("Catalog identity source or target is missing")
        source = entities[source_id]
        target = updates.setdefault(target_id, copy.deepcopy(entities[target_id]))
        if source.get("record_kind") != "directory" or target.get("record_kind") != "directory":
            raise ValueError("Catalog identity links require two directory records, not curated records")
        if source.get("parents") or target.get("parents") or any(any(edge.get("parent_id") == source_id for edge in node.get("parents", [])) for node in entities.values()):
            raise ValueError("Catalog identity source/target has structural edges requiring explicit migration")
        for key in ("source_registry_url", "target_registry_url", "official_url"):
            if not valid_url(link.get(key)):
                raise ValueError(f"Invalid catalog identity evidence URL: {key}")
        if source.get("registry_url") != link["source_registry_url"] or target.get("registry_url") != link["target_registry_url"]:
            raise ValueError("Catalog identity registry evidence does not match source records")
        if source.get("official_url") != link["official_url"] or target.get("official_url") != link["official_url"]:
            raise ValueError("Catalog identity official website evidence changed")
        if source.get("name") != link.get("source_name") or target.get("name") != link.get("target_name"):
            raise ValueError("Catalog identity reviewed source/target names changed")
        if not isinstance(link.get("note"), str) or not link["note"].strip():
            raise ValueError("Catalog identity review note required")
        try:
            date.fromisoformat(link["reviewed_at"])
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("Invalid catalog identity review date") from exc
        incoming_ids = source.get("identifiers", {})
        existing_ids = target.setdefault("identifiers", {})
        if not isinstance(incoming_ids, dict) or not isinstance(existing_ids, dict):
            raise ValueError("Invalid catalog identity identifiers")
        for key, value in incoming_ids.items():
            if key in existing_ids and str(existing_ids[key]) != str(value):
                raise ValueError(f"Catalog identity identifier conflict: {key}")
        existing_ids.update(copy.deepcopy(incoming_ids))
        target["aliases"] = list(dict.fromkeys(target.get("aliases", []) + source.get("aliases", []) + [source_id, source["name"]]))
        for field in ("name_zh", "official_url", "location", "city", "state", "institution_type", "listings"):
            if target.get(field) in (None, "", []) and source.get(field) is not None:
                target[field] = copy.deepcopy(source[field])
        for field in ("catalog_records", "sources"):
            values = target.setdefault(field, [])
            for item in source.get(field, []):
                if item not in values:
                    values.append(copy.deepcopy(item))
        target.setdefault("identity_sources", []).append({
            "record_id": source_id, "name": source["name"], "domain": source.get("domain"),
            "category": source.get("category"), "catalog_source": source.get("catalog_source"),
            "registry_url": source.get("registry_url"), "official_url": source.get("official_url"),
            "source_fields": copy.deepcopy(source.get("source_fields", {})),
        })
    entities.update(updates)
    for source_id in source_ids:
        del entities[source_id]
    return copy.deepcopy(links)
