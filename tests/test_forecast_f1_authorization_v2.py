"""Worker boundary tests: visual changes are independent, critical changes fail."""
import copy
import json
import shutil
from pathlib import Path
import pytest
from app.database import forecast_f1_authorization_v2 as v


@pytest.fixture
def isolated_manifest(monkeypatch,tmp_path):
    original=v.ROOT
    for folder in ('app','config'):
        shutil.copytree(original/folder,tmp_path/folder,ignore=shutil.ignore_patterns('__pycache__'))
    shutil.copyfile(original/'requirements.txt',tmp_path/'requirements.txt')
    monkeypatch.setattr(v,'ROOT',tmp_path)
    return tmp_path


def test_visual_changes_do_not_change_worker_manifest(isolated_manifest):
    root=isolated_manifest;before=v.artifacts()
    for name in ('styles.css','calendar/CalendarPage.tsx','calendar/earningsCompanyNames.ts','presentation.test.tsx'):
        p=root/'frontend/src'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('changed visual content',encoding='utf-8')
    assert v.artifacts()==before
    assert not any(p.startswith('frontend/') for p in before)


@pytest.mark.parametrize('path',['app/forecast_f1.py','app/forecast_f1_refresh.py','app/database/connection.py','config/forecast_f1_dispatch_policy.json','app/forecast_f1_bindings.py'])
def test_critical_change_is_detected(isolated_manifest,path):
    before=v.artifacts();p=isolated_manifest/path;p.write_bytes(p.read_bytes()+b'\n')
    assert v.artifacts()!=before


def test_missing_and_new_backend_dependency_stop(isolated_manifest):
    p=isolated_manifest/'app/unreviewed.py';p.write_text('pass')
    with pytest.raises(ValueError,match='inventory'):v.artifacts()
    p.unlink();(isolated_manifest/'app/forecast_f1.py').unlink()
    with pytest.raises(ValueError,match='inventory'):v.artifacts()


def test_manifest_cannot_omit_critical_path(isolated_manifest):
    p=isolated_manifest/v.SPEC;value=json.loads(p.read_text());value['paths'].remove('app/database/connection.py');p.write_text(json.dumps(value))
    with pytest.raises(ValueError,match='inventory'):v.artifacts()


def test_transitive_import_audit():
    audit=v.dependency_audit()
    assert ['app/forecast_f1_refresh.py','app/database/activate_forecast_f1.py'] in audit['local_import_edges']
    assert audit['dynamic_review_sites'] and not audit['frontend_financial_write_path']


def test_approval_gate_precedes_database():
    with pytest.raises(ValueError,match='Separate exact'):
        v.apply(object(),dict(target_label='localhost:5432/macrolens'),'wrong','wrong',{})


def test_partial_and_foreign_runtime_tokens_stop():
    for token in ({},{'version':2},{'version':1,'plan_sha256':'0'*64,'target':{},'artifacts':{}}):
        with pytest.raises(ValueError,match='token'):v.authorized(object(),token)
