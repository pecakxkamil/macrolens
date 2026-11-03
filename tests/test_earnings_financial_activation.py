"""Approval/backup gates before any SQL; synthetic files are not real restore evidence."""
import copy
import json
from unittest.mock import Mock
import pytest
from app.database import activate_earnings_financials as a
from app.database import activate_earnings as b

@pytest.mark.parametrize('target,token',[('wrong','hash'),('localhost:5432/macrolens','wrong')])
def test_approval_gate_before_connection(target,token):
    connection=Mock();plan={'target_label':'localhost:5432/macrolens'}
    with pytest.raises(ValueError,match='Explicit target'):
        a.apply(connection,plan,target,token)
    assert not connection.mock_calls

def test_frozen_artifacts_before_connection(monkeypatch):
    c=Mock();plan={'target_label':'db','version':1,'artifacts':{'old':'hash'}}
    monkeypatch.setattr(a,'artifacts',lambda:{'new':'hash'})
    with pytest.raises(ValueError,match='artifacts changed'):a.apply(c,plan,'db',b.digest(plan))
    assert not c.mock_calls

def manifest(tmp_path):
    dump=tmp_path/'synthetic-not-an-actual-backup.dump';dump.write_bytes(b'PGDMPunit-test')
    snapshots={'test':{'rows':1,'sha256':'test'}};target={'database':'unit'}
    proof={'source_target':target,'backup_sha256':b.file_hash(dump),'source_snapshots':snapshots,
           'restored_snapshots':snapshots,'restore_exit_code':0,'unvalidated_constraints':0,
           'schema_match':True,'owned_database_removed':True}
    path=tmp_path/'synthetic-restore-metadata.json';path.write_text(json.dumps(proof))
    return {'path':str(dump),'bytes':dump.stat().st_size,'sha256':b.file_hash(dump),
            'target':target,'format':'pg_dump_custom','toc_verified':True,'source_snapshots':snapshots,
            'restore_validation':{'path':str(path),'sha256':b.file_hash(path)}}

@pytest.mark.parametrize('change',[{'restore_exit_code':1},{'unvalidated_constraints':1},
 {'schema_match':False},{'owned_database_removed':False},{'restored_snapshots':{}},
 {'backup_sha256':'wrong'},{'source_target':{'database':'wrong'}}])
def test_restore_proof_required(tmp_path,change):
    m=manifest(tmp_path);proof_path=tmp_path/'synthetic-restore-metadata.json'
    proof=json.loads(proof_path.read_text());proof.update(change);proof_path.write_text(json.dumps(proof))
    m['restore_validation']['sha256']=b.file_hash(proof_path)
    with pytest.raises(ValueError,match='successful complete restore'):a.check_backup(m,m['target'])

def test_backup_and_receipt_tamper(tmp_path):
    m=manifest(tmp_path);a.check_backup(m,m['target'])
    with pytest.raises(ValueError):a.check_backup(m,{'database':'other'})
    changed=copy.deepcopy(m);changed['restore_validation']['sha256']='bad'
    with pytest.raises(ValueError,match='evidence hash'):a.check_backup(changed,m['target'])
    with open(m['path'],'ab') as stream:stream.write(b'tampered')
    with pytest.raises(ValueError,match='size/hash'):a.check_backup(m,m['target'])

def test_seed_scope_and_plan_hash():
    rows=a.seed();assert len(rows)==6 and sum(len(r['observations']) for r in rows)==12
    assert not any(r['ticker']=='NVDA' and r['fiscal_quarter']==3 for r in rows)
    plan={'target':'one','backup':'one'};changed={**plan,'backup':'two'}
    assert b.digest(plan)!=b.digest(changed)
