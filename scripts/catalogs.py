"""Merge reproducible official directories without pretending they are researched dossiers."""
import copy
import hashlib
import json
import re
from datetime import date


def merge_catalogs(directory, entities, root, valid_url):
    metadata, seen = [], set(entities)
    for file in sorted(directory.glob('*.json')):
        catalog = json.loads(file.read_text(encoding='utf-8'))
        meta, records = catalog['metadata'], catalog['records']
        if not isinstance(records, list) or not meta.get('id'):
            raise ValueError(f'{file}: invalid catalog')
        for field in ('raw_count','included_count','excluded_count'):
            if type(meta.get(field)) is not int or meta[field] < 0:
                raise ValueError(f'{file}: {field} must be a nonnegative integer')
        date.fromisoformat(meta['retrieved_at'])
        if not valid_url(meta['source_url']):
            raise ValueError(f'{file}: invalid source URL')
        snapshots = meta.get('raw_files') or ([{'path':meta['raw_file'],'sha256':meta['sha256']}] if meta.get('raw_file') else [])
        if not snapshots:
            raise ValueError(f'{file}: raw snapshot provenance required')
        for snapshot in snapshots:
            path = (root / snapshot['path']).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                raise ValueError(f'{file}: snapshot path must be a repository file')
            if hashlib.sha256(path.read_bytes()).hexdigest() != snapshot['sha256']:
                raise ValueError(f'{file}: snapshot SHA-256 mismatch')
        if meta['included_count'] != len(records):
            raise ValueError(f'{file}: catalog included_count mismatch')
        catalog_ids, matched = set(), set()
        for raw in records:
            rid = raw['id']
            if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', rid) or rid in catalog_ids or rid in seen:
                raise ValueError(f'{file}: invalid or duplicate catalog id {rid}')
            catalog_ids.add(rid)
            if raw.get('domain') not in {'government','university','enterprise','finance'} or not raw.get('name'):
                raise ValueError(f'{file}: missing identity/domain for {rid}')
            if raw.get('catalog_source') != meta['id']:
                raise ValueError(f'{file}: inconsistent catalog source for {rid}')
            for field in ('official_url','registry_url'):
                if raw.get(field) is not None and not valid_url(raw[field]):
                    raise ValueError(f'{file}: invalid {field} for {rid}')
            loc = raw.get('location')
            if loc is not None:
                if not isinstance(loc, dict) or not all(isinstance(loc.get(k),str) and loc[k].strip() for k in ("city","state")) or loc.get("precision") not in {"city","campus","headquarters"}:
                    raise ValueError(f"{file}: incomplete location for {rid}")
                if any(type(loc.get(k)) not in (float,int) for k in ('lat','lon')) or not -90 <= loc['lat'] <= 90 or not -180 <= loc['lon'] <= 180 or not valid_url(loc.get('evidence_url')):
                    raise ValueError(f'{file}: invalid location for {rid}')
            target = raw.get('curated_id')
            provenance = {'source_id':meta['id'],'record_id':rid,'retrieved_at':meta['retrieved_at'],'source_period':meta.get('source_period'),'registry_url':raw.get('registry_url')}
            if target:
                if target not in entities or entities[target].get('record_kind') == 'directory' or target in matched:
                    raise ValueError(f'{file}: invalid or duplicate curated crosswalk {target}')
                node = entities[target]
                matched.add(target)
                for field in ('location','official_url','city','state','institution_type','listings','source_fields'):
                    if not node.get(field) and raw.get(field) is not None:
                        node[field] = copy.deepcopy(raw[field])
                for key,value in raw.get('identifiers',{}).items():
                    if key in node.get('identifiers',{}) and str(node['identifiers'][key]) != str(value):
                        raise ValueError(f'{file}: identifier conflict for {target}: {key}')
                node.setdefault('identifiers',{}).update(raw.get('identifiers',{}))
                node['aliases'] = list(dict.fromkeys(node.get('aliases',[]) + raw.get('aliases',[]) + [rid]))
                node.setdefault('catalog_records',[]).append(provenance)
            else:
                node = copy.deepcopy(raw)
                node.update({'parents':[], 'sources':[{'url':raw.get('registry_url') or meta['source_url'],'description':meta['title']}],
                    'publications':[], 'financial_profile':[], 'leader':None,'employee_count':None,'function':None,
                    'verification_status':'unverified','verified_at':None,'catalog_records':[provenance],
                    'record_kind':'directory','research_notes':'此条目来自官方名录。名录收录不代表职责、治理、负责人、财务或现行隶属关系已逐项核验。'})
                node.setdefault('name_zh',None)
                node.setdefault('aliases',[])
                node.setdefault('official_url',None)
                node.setdefault('location',None)
                entities[rid] = node
            seen.add(rid)
        meta = copy.deepcopy(meta)
        meta.update({'matched_curated_count':len(matched),'new_directory_count':len(records)-len(matched)})
        metadata.append(meta)
    return metadata
