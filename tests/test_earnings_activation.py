"""Approval and backup gates do not touch a database or publisher."""
import copy
import hashlib
from unittest.mock import Mock
import pytest
from app.database import activate_earnings as activation


@pytest.mark.parametrize('target,token',[('wrong','hash'),('localhost:5432/macrolens','wrong')])
def test_approval_required_before_connection(target,token):
    connection=Mock()
    plan={'target_label':'localhost:5432/macrolens'}
    with pytest.raises(ValueError,match='Explicit target'):
        activation.apply(connection,plan,target,token)
    assert not connection.mock_calls


def test_artifact_drift_before_db(monkeypatch):
    connection=Mock();plan={'version':1,'target_label':'db','artifacts':{'old':'hash'}}
    monkeypatch.setattr(activation,'artifacts',lambda:{'new':'hash'})
    with pytest.raises(ValueError,match='artifacts changed'):
        activation.apply(connection,plan,'db',activation.digest(plan))
    assert not connection.mock_calls


def backup(tmp_path):
    path=tmp_path/'synthetic-not-a-production-backup.dump';path.write_bytes(b'PGDMPsynthetic')
    return {'path':str(path),'target':{'database':'test'},'format':'pg_dump_custom',
            'toc_verified':True,'bytes':path.stat().st_size,'sha256':activation.file_hash(path)}


def test_backup_hash_and_target(tmp_path):
    manifest=backup(tmp_path);activation.check_backup(manifest,{'database':'test'})
    with pytest.raises(ValueError,match='exact cluster'):
        activation.check_backup(manifest,{'database':'other'})
    with open(manifest['path'],'ab') as stream:stream.write(b'changed')
    with pytest.raises(ValueError,match='size/hash'):
        activation.check_backup(manifest,manifest['target'])


@pytest.mark.parametrize('change',[{'format':'plain'},{'toc_verified':False}])
def test_backup_verification_required(tmp_path,change):
    manifest=backup(tmp_path);manifest.update(change)
    with pytest.raises(ValueError):activation.check_backup(manifest,manifest['target'])


def test_isolated_initializer_unchanged():
    from app.database.init_earnings_db import initialize
    connection=Mock();connection.info.dbname='macrolens'
    with pytest.raises(ValueError,match='owned macrolens_earnings'):
        initialize(connection)
    connection.transaction.assert_not_called()


def test_plan_token_covers_every_field():
    plan={'target':'one','backup':'old','artifacts':{'one':'a'}}
    changed=copy.deepcopy(plan);changed['backup']='different'
    assert activation.digest(plan)!=activation.digest(changed)
