"""Prove absence of factory/other-customer data in completed downloads."""
import json
import os
import subprocess
import sys
import zipfile
from copy import deepcopy
from pathlib import Path

import pytest

from manufacturing.website_orb.orchestrator import manufacture_website_orb
from manufacturing.website_orb.package_audit import audit_package
from test_website_orb_manufacturer import _evidence


def build(tmp_path, domain, term, alias):
    document = json.loads(json.dumps(_evidence()).replace('example.com', domain).replace('Known Product', term))
    document['site_id'] = domain
    document['scan_id'] = domain + '-scan-2'
    document['lexical_index']['aliases']['nav: Home'] = [alias]
    result = manufacture_website_orb(evidence=document, output_root=tmp_path, build_id=domain,
                                    owner_verification={'owner': 'test-owner', 'approved_artifacts': ['*']}, ephemeral=True)
    assert result['delivery_ready'], result['failure_reasons']
    return document, result


def test_downloads_are_isolated_and_boot_without_factory(tmp_path):
    source, one = build(tmp_path, 'garden.example', 'Orchid Atlas', 'garden welcome')
    _, two = build(tmp_path, 'marine.example', 'Reef Compass', 'marine welcome')
    for result, own, foreign in ((one, 'Orchid Atlas', 'Reef Compass'), (two, 'Reef Compass', 'Orchid Atlas')):
        assert result['validation_results']['isolation_audit']['passed']
        assert result['validation_results']['isolation_audit']['observed'] == []
        with zipfile.ZipFile(result['package_paths']['orbpack']) as archive:
            text = '\n'.join(archive.read(name).decode('utf8', errors='replace') for name in archive.namelist() if not name.endswith('/'))
            assert own in text and foreign not in text
            manifest = json.loads(archive.read('manifest.json'))
            lineage = manifest['build_lineage']
            assert lineage['site_id'] == result['site_id']
            assert lineage['scan']['scan_id'] == result['source_scan_id']
            assert lineage['artifacts']['apriori/site_skg.json']['sha256']
            assert lineage['artifacts']['pointers.json']['schema']
            assert not any('compiled_orb/' in name or name.startswith('dock-station/') for name in archive.namelist())
            assert all(not name.endswith(('.zip', '.pdf', '.wav')) for name in archive.namelist())
    installed = tmp_path / 'independent-install'
    with zipfile.ZipFile(one['package_paths']['orbpack']) as archive:
        archive.extractall(installed)
    runtime = installed / 'website-orb'
    env = {**os.environ, 'PYTHONPATH': str(runtime), 'PYTHONDONTWRITEBYTECODE': '1',
           'ORB_WEAVER_VAULT_ROOT': str(runtime / 'runtime/vault_system')}
    probe = '''
import socket
def no_network(*args, **kwargs):
    raise AssertionError('An independent text runtime must not make network calls')
socket.socket.connect = no_network
from backend.app import app
from fastapi.testclient import TestClient
with TestClient(app) as client:
    assert client.get('/health').status_code == 200
    bootstrap = client.get('/orb/bootstrap').json()
    assert bootstrap['site_id'] == 'garden.example'
    assert client.get('/orb/widget.js').status_code == 200
    answer = client.post('/orb/answer-text', json={'message': 'How much is Orchid Atlas?', 'route': '/product'}).json()
    assert '49' in answer['answer'], answer
    assert answer['governance_trace']['status'] == 'approved'
    assert client.get('/orb/pointer-map', params={'route': '/unknown'}).json()['records'] == []
    assert client.post('/orb/dock/action', json={'action': 'open_app'}).status_code == 403
    assert client.get('/orb/bootstrap', headers={'Origin': 'https://unrelated.example'}).headers.get('access-control-allow-origin') is None
print('independent runtime passed')
'''
    run = subprocess.run([sys.executable, '-c', probe], cwd=runtime, env=env, text=True, capture_output=True)
    assert run.returncode == 0, run.stderr + run.stdout
    check = subprocess.run([sys.executable, 'run.py', '--check'], cwd=runtime, env=env, text=True, capture_output=True)
    assert check.returncode == 0, check.stderr
    config = runtime / 'runtime/vault_system/payload/site_config.json'
    config.write_text(config.read_text().replace('Website ORB', 'UNAPPROVED OVERRIDE'))
    changed = subprocess.run([sys.executable, 'run.py', '--check'], cwd=runtime, env=env, text=True, capture_output=True)
    assert changed.returncode != 0 and 'hash mismatch' in changed.stderr


@pytest.mark.parametrize('context', [
    {'latest_context': {'site_name': 'Factory default'}},
    {'site_id': 'site-1', 'domain': 'example.com', 'source_scan_id': 'old-scan'},
])
def test_unbound_or_stale_cache_is_rejected(tmp_path, context):
    result = manufacture_website_orb(evidence=_evidence(), source_context=context, output_root=tmp_path, ephemeral=True)
    assert result['status'] == 'failed'
    assert any('source_context' in item for item in result['failure_reasons'])


def test_negative_audit_finds_injected_factory_fallback(tmp_path):
    path = tmp_path / 'contaminated.orbpack'
    with zipfile.ZipFile(path, 'w') as archive:
        archive.writestr('website-orb/assets/bad.js', 'fetch("https://orbweaver.spruked.com/api/orb/site-world")')
    result = audit_package(path, _evidence(), {})
    assert not result['passed']
    assert any(item.get('marker') == 'orbweaver.spruked.com' for item in result['findings'])


def test_same_scan_context_cannot_overlay_evidence(tmp_path):
    evidence = _evidence()
    result = manufacture_website_orb(evidence=evidence, output_root=tmp_path, ephemeral=True,
        source_context={'site_id': 'site-1', 'domain': 'example.com', 'source_scan_id': 'scan-1',
                        'site_world': {'key_facts': ['POISONED FACT'], 'route_hints': {'bad': '/founding-beta'}},
                        'tool_cache': {'entries': [{'spoken_output': 'POISONED FACT'}]}},
        owner_verification={'owner': 'test-owner', 'approved_artifacts': ['*']})
    assert result['delivery_ready'], result['failure_reasons']
    with zipfile.ZipFile(result['package_paths']['orbpack']) as archive:
        assert b'POISONED FACT' not in b''.join(archive.read(name) for name in archive.namelist())
