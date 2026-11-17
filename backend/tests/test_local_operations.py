"""Offline operations tests: ephemeral SQLite and pytest temporary files only."""
import io
import importlib
import json
from pathlib import Path
import sys
import tarfile
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import xml.etree.ElementTree as ET
import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, override_settings
from apps.accounts.models import User
from apps.accounts.services.local_demotion import OWNER, SYNTHETIC, demote_local_verification_admin
from apps.accounts.services.auth_service import generate_jwt_pair

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'deploy'))
backup = importlib.import_module('local_backup')

@pytest.fixture
def admins(db):
    owner = User.objects.create_superuser(id=OWNER, phone_number='+998909990010', password='OwnerFixture2026!', full_name='Owner')
    subject = User.objects.create_superuser(id=SYNTHETIC, phone_number='+998909990011', password='SubjectFixture2026!', full_name='Synthetic')
    return owner, subject

@pytest.mark.django_db
def test_demotion_revokes_subject_preserves_owner_and_history(admins, api_client):
    owner, subject = admins
    old, other = generate_jwt_pair(subject), generate_jwt_pair(owner)
    browser, owner_browser = Client(), Client()
    browser.force_login(subject); owner_browser.force_login(owner)
    before = User.objects.values().get(pk=OWNER)
    password, count = subject.password, User.objects.count()
    from django.contrib.auth.models import Group
    from django.contrib.admin.models import LogEntry
    group = Group.objects.create(name='fixture privilege'); subject.groups.add(group)
    with override_settings(LOCAL_TARGET_KIND='work'):
        receipt = demote_local_verification_admin(SYNTHETIC, OWNER, owner_approved=True)
    subject.refresh_from_db()
    assert not subject.is_staff and not subject.is_superuser and subject.role == 'WORKER'
    assert subject.password == password and subject.is_active and subject.token_version == 2
    assert User.objects.count() == count and User.objects.values().get(pk=OWNER) == before
    assert group.pk in receipt['before']['groups'] and Group.objects.filter(pk=group.pk).exists()
    assert not subject.groups.exists()
    assert browser.get('/django-admin/').status_code == 302
    assert owner_browser.get('/django-admin/').status_code == 200
    api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + old['access'])
    assert api_client.get('/api/v1/admin/dashboard/').status_code == 401
    assert api_client.post('/api/v1/auth/token/refresh/', {'refresh': old['refresh']}).status_code == 401
    new = generate_jwt_pair(subject)
    api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + new['access'])
    assert api_client.get('/api/v1/admin/dashboard/').status_code == 403
    api_client.credentials(HTTP_AUTHORIZATION='Bearer ' + other['access'])
    assert api_client.get('/api/v1/admin/dashboard/').status_code == 200
    assert LogEntry.objects.get(action_flag=2).user_id == OWNER

@pytest.mark.django_db
def test_demotion_rolls_back_on_revocation_failure(admins):
    owner, subject = admins
    with override_settings(LOCAL_TARGET_KIND='work'), patch('apps.accounts.services.local_demotion._blacklist_all_user_tokens', side_effect=RuntimeError('fixture')), pytest.raises(RuntimeError):
        demote_local_verification_admin(SYNTHETIC, OWNER, owner_approved=True)
    subject.refresh_from_db()
    assert subject.is_admin_user and subject.is_superuser and subject.token_version == 1

@pytest.mark.parametrize('approved,account,actor', [(False,SYNTHETIC,OWNER),(True,OWNER,OWNER),(True,SYNTHETIC,SYNTHETIC)])
def test_unauthorized_demotion_never_queries(approved, account, actor):
    with override_settings(LOCAL_TARGET_KIND='work'), patch('apps.accounts.services.local_demotion.User.objects.select_for_update') as query, pytest.raises(ValidationError):
        demote_local_verification_admin(account, actor, owner_approved=approved)
    query.assert_not_called()

@pytest.mark.django_db
def test_unusable_owner_blocks_demotion(admins):
    owner, subject = admins; owner.set_unusable_password(); owner.save()
    with override_settings(LOCAL_TARGET_KIND='work'), pytest.raises(ValidationError):
        demote_local_verification_admin(SYNTHETIC, OWNER, owner_approved=True)
    subject.refresh_from_db(); assert subject.is_admin_user

def test_demotion_command_default_no_queries_apply_requires_approval():
    with patch('django.db.backends.base.base.BaseDatabaseWrapper.ensure_connection', side_effect=AssertionError('query')):
        output = io.StringIO(); call_command('demote_local_verification_admin', stdout=output)
        assert 'REQUIRES APPROVAL' in output.getvalue()
        with pytest.raises(CommandError): call_command('demote_local_verification_admin', apply=True)

def approvals():
    now = datetime(2026,11,17,tzinfo=timezone.utc)
    runtime = dict(approved_by='fixture', expires_at=(now+timedelta(days=7)).isoformat(), target=dict(host='postgres-work',port='5432',dbname='ishchi_marketplace_local',user='ishchi_local_app'), operations=['connect'])
    redis = dict(approved_by='fixture', expires_at=runtime['expires_at'], target=dict(host='redis-work',port=6379,database=0,user='ishchi_local_app'), operations=['cache'])
    doc = dict(approved_by='fixture', expires_at=(now+timedelta(days=1)).isoformat(), plan=backup.PLAN, operations=list(backup.SCOPES), recipient='age1fixture')
    return now, doc, runtime, redis

@pytest.mark.parametrize('case', ['expired','runtime-expired','too-long','wrong-db','wrong-role','wrong-redis','scope','unapproved'])
def test_backup_approval_fail_closed(case):
    now, doc, runtime, redis = approvals()
    if case == 'expired': doc['expires_at'] = now.isoformat()
    if case == 'runtime-expired': runtime['expires_at'] = now.isoformat()
    if case == 'too-long': doc['expires_at'] = (now+timedelta(days=8)).isoformat()
    if case == 'wrong-db': runtime['target']['dbname'] = 'refused-database'
    if case == 'wrong-role': runtime['target']['user'] = 'refused-role'
    if case == 'wrong-redis': redis['target']['database'] = 1
    if case == 'scope': doc['operations'] = []
    if case == 'unapproved': doc['approved_by'] = ''
    with pytest.raises(backup.ApprovalRequired): backup.authorize(doc, runtime, redis, now)

def test_overlap_prevention_and_release(tmp_path):
    with backup.exclusive_lock(tmp_path/'lock'):
        with pytest.raises(backup.Overlap):
            with backup.exclusive_lock(tmp_path/'lock'): pass
    with backup.exclusive_lock(tmp_path/'lock'): pass

@pytest.mark.parametrize('current', [{'tombstones':['new']},{'outbox':[['id','new','done']]},{'media':[]}])
def test_stale_ledger_blocks_recovery(current):
    with pytest.raises(backup.BackupError, match='ERASURE_LEDGER_REFRESH_REQUIRED'):
        backup.require_fresh_ledger({'state':{'tombstones':[],'outbox':[],'media':['file']}}, current)

def test_fresh_ledger_handles_json_tuple_roundtrip():
    backup.require_fresh_ledger({'state':{'outbox':[['id','time']]}}, {'outbox':[('id','time')]})

def archive_fixture(tmp_path, monkeypatch):
    key = tmp_path/'key'; key.write_text('# fixture\nAGE-SECRET-KEY-OFFLINE-TEST\n')
    ledger = tmp_path/'erasure-ledger-scheduled-fixture.json.age'; ledger.write_bytes(b'cipher ledger')
    monkeypatch.setattr(backup, 'RECOVERY', tmp_path)
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode='w') as archive:
        info = tarfile.TarInfo('media/a.txt'); info.size=3; archive.addfile(info, io.BytesIO(b'abc'))
    folder = tmp_path/'backup'; folder.mkdir()
    for name in ['postgres.dump.age','media.tar.age','manifest.json.age']: (folder/name).write_bytes(name.encode())
    state = {'tombstones':[]}
    manifest = dict(archives={n:dict(bytes=(folder/n).stat().st_size,sha256=backup.checksum(folder/n)) for n in ['postgres.dump.age','media.tar.age']}, media=[dict(name='a.txt',sha256=backup.hashlib.sha256(b'abc').hexdigest())], ledger=dict(path=str(ledger),sha256=backup.checksum(ledger)), erasure_state=state)
    bodies = {'postgres.dump.age':b'PGDMPfixture','media.tar.age':data.getvalue(),'manifest.json.age':json.dumps(backup.signed(manifest,key)).encode(),ledger.name:json.dumps(backup.signed({'state':state},key)).encode()}
    monkeypatch.setattr(backup.recovery, 'decrypt', lambda path,identity:bodies[path.name])
    (folder/'COMPLETE.json').write_text(json.dumps(dict(manifest_sha256=backup.checksum(folder/'manifest.json.age'))))
    return folder, key, bodies

@pytest.mark.parametrize('case', ['valid','incomplete','truncated','manifest','media','forged'])
def test_corrupt_incomplete_archive_detection(tmp_path, monkeypatch, case):
    folder, key, bodies = archive_fixture(tmp_path, monkeypatch)
    if case == 'incomplete': (folder/'COMPLETE.json').unlink()
    if case == 'truncated': (folder/'postgres.dump.age').write_bytes(b'partial')
    if case == 'manifest': (folder/'manifest.json.age').write_bytes(b'changed')
    if case == 'media': bodies['media.tar.age'] = b'bad tar'
    if case == 'forged':
        doc=json.loads(bodies['manifest.json.age']); doc['payload']['retention_days']=1; bodies['manifest.json.age']=json.dumps(doc).encode()
    if case == 'valid': assert backup.verify_archive_set(folder,key,lambda data:None)
    else:
        with pytest.raises((backup.BackupError,tarfile.ReadError)): backup.verify_archive_set(folder,key,lambda data:None)

def test_cleanup_preserves_all_published_and_unrelated_files(tmp_path):
    names=['postgres.dump.age','media.tar.age','manifest.json.age','older.age']
    for name in names+['postgres.dump.age.partial']: (tmp_path/name).write_bytes(b'fixture')
    backup.cleanup_partials(tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == sorted(names)

@pytest.mark.parametrize('failure', ['stop','encrypt'])
def test_partial_stop_or_encryption_failure_still_resumes(tmp_path, monkeypatch, failure):
    now, doc, runtime, redis = approvals()
    doc['expires_at']=(datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
    for name,d in [('work-db-authorization.json',runtime),('work-redis-authorization.json',redis)]: (tmp_path/name).write_text(json.dumps(d))
    (tmp_path/'identity.agekey').write_text('AGE-SECRET-KEY-OFFLINE-TEST')
    (tmp_path/'local_migration_password').write_text('fixture only')
    for name in ['PRIVATE','RECOVERY','BACKUPS']: monkeypatch.setattr(backup,name,tmp_path)
    monkeypatch.setattr(backup,'authorize',lambda *a:doc['recipient'])
    monkeypatch.setattr(backup,'require_private_acl',lambda p:None); monkeypatch.setattr(backup,'restrict_new_directory',lambda p:None)
    class Response:
        status=200
        def __enter__(self): return self
        def __exit__(self,*a): pass
    monkeypatch.setattr(backup.urllib.request,'build_opener',lambda *a:type('Opener',(),{'open':lambda *a,**kw:Response()})())
    runner=backup.Runner()
    def call(cmd,**kwargs):
        if 'stop' in cmd and failure=='stop': raise RuntimeError('partial stop')
        if cmd[-1]=='--version': return 'v1.3.2'
        return doc['recipient']
    monkeypatch.setattr(runner,'call',call)
    if failure=='encrypt':
        import psycopg
        class Source:
            def execute(self,*a):return self
            def fetchone(self):return ('ishchi_marketplace_local','ishchi_local_migrator','ishchi_local_owner')
            def close(self):pass
        monkeypatch.setattr(psycopg,'connect',lambda **kw:Source())
        monkeypatch.setattr(backup.recovery,'fingerprint',lambda *a:{'rows':{}})
        monkeypatch.setattr(runner,'media',lambda:[])
        monkeypatch.setattr(backup,'ledger_state',lambda *a:{})
        monkeypatch.setattr(backup.recovery,'encrypt_json',lambda *a:(_ for _ in ()).throw(RuntimeError('encryption failure')))
    resumed=[]; monkeypatch.setattr(runner,'resume',lambda:resumed.append(True))
    with pytest.raises(RuntimeError): runner.execute(doc)
    assert resumed == [True] and not (tmp_path/'backup-resume-required.json').exists()

def test_expired_execution_returns_renewal_before_runner(tmp_path,monkeypatch,capsys):
    now,doc,runtime,redis=approvals();doc['expires_at']='2000-01-01T00:00:00Z'
    monkeypatch.setattr(backup,'PRIVATE',tmp_path);monkeypatch.setattr(backup,'RECOVERY',tmp_path);monkeypatch.setattr(backup,'APPROVAL',tmp_path/'approval.json')
    for name,d in [('approval.json',doc),('work-db-authorization.json',runtime),('work-redis-authorization.json',redis)]: (tmp_path/name).write_text(json.dumps(d))
    with patch.object(backup.Runner,'execute',side_effect=AssertionError('runner entered')):
        assert backup.main(['--execute'])==3
    assert 'REQUIRES APPROVAL' in capsys.readouterr().out

def test_deadline_blocks_subprocess(monkeypatch):
    runner=backup.Runner();runner.deadline=0
    with patch.object(backup.recovery,'run',side_effect=AssertionError('subprocess entered')),pytest.raises(backup.BackupError,match='DEADLINE'):
        runner.call(['not executed'])

@pytest.mark.skipif(sys.platform!='win32',reason='Windows ACL regression')
def test_new_backup_directory_has_restricted_windows_acl(tmp_path):
    folder=tmp_path/'new-test-only';folder.mkdir()
    backup.restrict_new_directory(folder)
    backup.require_private_acl(folder)
    (folder/'synthetic.txt').write_text('fixture')
    backup.require_private_acl(folder/'synthetic.txt')

@pytest.mark.skipif(sys.platform!='win32',reason='Windows ACL regression')
def test_broad_read_acl_is_rejected(tmp_path):
    folder=tmp_path/'new-test-only';folder.mkdir()
    backup.restrict_new_directory(folder)
    backup.recovery.run(['icacls.exe',str(folder),'/grant','*S-1-1-0:R'])
    with pytest.raises(backup.BackupError,match='ACL_REQUIRED'):backup.require_private_acl(folder)

def test_default_plan_no_secret_access_and_fixed_failure_reporting(tmp_path, monkeypatch, capsys):
    with patch.object(Path,'read_text',side_effect=AssertionError('secret read')): assert backup.main([])==0
    assert 'PREPARED ONLY' in capsys.readouterr().out
    now,doc,runtime,redis=approvals()
    monkeypatch.setattr(backup,'RECOVERY',tmp_path); monkeypatch.setattr(backup,'PRIVATE',tmp_path); monkeypatch.setattr(backup,'APPROVAL',tmp_path/'approval.json')
    for name,d in [('approval.json',doc),('work-db-authorization.json',runtime),('work-redis-authorization.json',redis)]: (tmp_path/name).write_text(json.dumps(d))
    monkeypatch.setattr(backup,'authorize',lambda *a:'age1fixture')
    monkeypatch.setattr(backup.Runner,'execute',lambda *a:(_ for _ in ()).throw(RuntimeError('DO_NOT_LEAK_PASSWORD')))
    assert backup.main(['--execute'])==1
    assert 'DO_NOT_LEAK_PASSWORD' not in capsys.readouterr().out
    assert 'DO_NOT_LEAK_PASSWORD' not in (tmp_path/'scheduled-backup-status.json').read_text()

def test_disabled_task_is_bounded_interactive_nonoverlapping():
    ns={'t':'http://schemas.microsoft.com/windows/2004/02/mit/task'}
    root=ET.parse(ROOT/'deploy/local/ishchi-backup-task.xml').getroot()
    for path,text in [('Settings/Enabled','false'),('Settings/MultipleInstancesPolicy','IgnoreNew'),('Settings/ExecutionTimeLimit','PT45M'),('Principals/Principal/LogonType','InteractiveToken')]:
        assert root.find('/'.join('t:'+part for part in path.split('/')),ns).text == text
    assert root.find('t:Triggers/t:CalendarTrigger/t:StartBoundary',ns).text.endswith('20:00:00+05:00')
    assert 'password' not in root.find('t:Actions/t:Exec/t:Arguments',ns).text.lower()

def test_failure_logs_are_retained_without_overwriting_previous_events(tmp_path,monkeypatch):
    monkeypatch.setattr(backup,'RECOVERY',tmp_path)
    backup.persist_status({'status':'FAIL'},1)
    backup.persist_status({'status':'PASS'},0)
    records=[json.loads(p.read_text()) for p in (tmp_path/'backup-logs').glob('*.json')]
    assert len(records)==2 and {r['status'] for r in records}=={'FAIL','PASS'}

def test_resume_only_requires_runtime_authorization_and_clears_only_its_marker(tmp_path,monkeypatch):
    now,doc,runtime,redis=approvals()
    monkeypatch.setattr(backup,'PRIVATE',tmp_path);monkeypatch.setattr(backup,'RECOVERY',tmp_path)
    for name,d in [('work-db-authorization.json',runtime),('work-redis-authorization.json',redis)]: (tmp_path/name).write_text(json.dumps(d))
    marker=tmp_path/'backup-resume-required.json';marker.write_text('{}')
    preserved=tmp_path/'previous.dump.age';preserved.write_bytes(b'fixture')
    monkeypatch.setattr(backup,'authorize_runtime',lambda *a:now+timedelta(days=1))
    monkeypatch.setattr(backup,'require_private_acl',lambda p:None)
    called=[];monkeypatch.setattr(backup.Runner,'resume',lambda self:called.append(True))
    with patch.object(backup.Runner,'execute',side_effect=AssertionError('backup entered')):
        assert backup.main(['--resume-only'])==0
    assert called==[True] and not marker.exists() and preserved.read_bytes()==b'fixture'

@pytest.mark.parametrize('production,kind',[(True,'work'),(False,'test'),(False,'')])
def test_wrong_demotion_environment_blocks_before_queries(production,kind):
    from django.core.exceptions import ImproperlyConfigured
    with override_settings(IS_PRODUCTION=production,LOCAL_TARGET_KIND=kind),patch('apps.accounts.services.local_demotion.User.objects.select_for_update') as lookup,pytest.raises(ImproperlyConfigured):
        demote_local_verification_admin(SYNTHETIC,OWNER,owner_approved=True)
    lookup.assert_not_called()

def test_short_authorization_window_blocks_before_pause_or_secret_access(tmp_path,monkeypatch):
    now,doc,runtime,redis=approvals()
    doc['expires_at']=(datetime.now(timezone.utc)+timedelta(minutes=5)).isoformat()
    monkeypatch.setattr(backup,'PRIVATE',tmp_path)
    for name,d in [('work-db-authorization.json',runtime),('work-redis-authorization.json',redis)]: (tmp_path/name).write_text(json.dumps(d))
    monkeypatch.setattr(backup,'authorize',lambda *a:'age1fixture')
    with patch.object(backup,'require_private_acl',side_effect=AssertionError('preflight passed window')),pytest.raises(backup.ApprovalRequired,match='WINDOW'):
        backup.Runner().execute(doc)

@pytest.mark.django_db
def test_empty_memberships_need_no_runtime_permission_delete(admins):
    from django.db import connection
    def deny_membership_delete(execute,sql,params,many,context):
        if sql.lstrip().upper().startswith('DELETE') and any(name in sql for name in ['accounts_user_groups','accounts_user_user_permissions']):
            raise AssertionError('Runtime must not DELETE empty privilege memberships')
        return execute(sql,params,many,context)
    with override_settings(LOCAL_TARGET_KIND='work'),connection.execute_wrapper(deny_membership_delete):
        result=demote_local_verification_admin(SYNTHETIC,OWNER,owner_approved=True)
    assert result['sessions_revoked']
