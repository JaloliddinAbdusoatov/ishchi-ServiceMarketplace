"""Backup-only extension of local_recovery. Default: offline plan, no operations.
Execution/install require independent owner approval. No restore or retention deletion.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tarfile
from pathlib import PurePosixPath
import time
import urllib.request
import local_recovery as recovery

ROOT=recovery.ROOT
PRIVATE=recovery.PRIVATE
RECOVERY=recovery.RECOVERY
BACKUPS=recovery.BACKUPS
APPROVAL=RECOVERY/"scheduled-backup-authorization.json"
MAX_SECONDS=900
SCOPES={"encrypted_pg_media_backup","read_migrator_backup","pause_resume_application","checkpoint_ledger_export"}
SOURCE={"host":"127.0.0.1","port":55432,"dbname":"ishchi_marketplace_local","user":"ishchi_local_migrator","set_role":"ishchi_local_owner"}
PLAN={"source":SOURCE,"destination":str(BACKUPS),"ledger_directory":str(RECOVERY),"retention_days":30,"delete_backups":False}
MEDIA_CODE="""import json,hashlib;from pathlib import Path
root=Path('/app/media');out=[]
for p in sorted(root.rglob('*')):
 if p.is_symlink():raise RuntimeError('Media link refused')
 if p.is_file():out.append({'name':p.relative_to(root).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
print(json.dumps(out))
"""
TAR_CODE="""import tarfile
from pathlib import PurePosixPath,sys;from pathlib import Path
root=Path('/app/media')
if any(p.is_symlink() for p in root.rglob('*')):raise RuntimeError('Media link refused')
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as a:a.add(root,arcname='media')
"""

class BackupError(RuntimeError): pass
class ApprovalRequired(BackupError): pass
class Overlap(BackupError): pass


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),default=str).encode()
def checksum(path):
    digest=hashlib.sha256()
    with path.open('rb') as file:
        for block in iter(lambda:file.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()

def load_approval(path):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError,UnicodeError):raise ApprovalRequired('EXACT_BACKUP_APPROVAL_REQUIRED') from None

def expires(doc,now):
    try:
        end=datetime.fromisoformat(doc['expires_at'].replace('Z','+00:00'))
        if not doc['approved_by'].strip() or end<=now:raise ValueError()
        return end
    except (KeyError,ValueError,TypeError,AttributeError):raise ApprovalRequired('RENEWAL_REQUIRED') from None

def authorize_runtime(runtime,redis_doc,now=None):
    now=now or datetime.now(timezone.utc)
    end=min(expires(runtime,now),expires(redis_doc,now))
    expected={'host':'postgres-work','port':'5432','dbname':'ishchi_marketplace_local','user':'ishchi_local_app'}
    if runtime.get('target')!=expected or 'connect' not in runtime.get('operations',[]):raise ApprovalRequired('RUNTIME_TARGET_MISMATCH')
    target=redis_doc.get('target',{})
    if target.get('host')!='redis-work' or str(target.get('port'))!='6379' or str(target.get('database'))!='0' or target.get('user')!='ishchi_local_app' or 'cache' not in redis_doc.get('operations',[]):
        raise ApprovalRequired('REDIS_TARGET_MISMATCH')
    return end

def authorize(doc,runtime,redis_doc,now=None):
    now=now or datetime.now(timezone.utc)
    end=expires(doc,now)
    if end>authorize_runtime(runtime,redis_doc,now):raise ApprovalRequired('BACKUP_EXCEEDS_RUNTIME_AUTHORIZATION')
    if doc.get('plan')!=PLAN or set(doc.get('operations',[]))!=SCOPES or not doc.get('recipient','').startswith('age1'):
        raise ApprovalRequired('EXACT_BACKUP_APPROVAL_REQUIRED')
    return doc['recipient']

@contextmanager
def exclusive_lock(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    file=path.open('a+b');file.seek(0);file.write(b'0');file.flush();file.seek(0)
    try:
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(file.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(file.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:raise Overlap('BACKUP_ALREADY_RUNNING') from None
        yield
    finally:file.close()  # Kernel releases lock, including after process failure.


def restrict_new_directory(path):
    # Only a new empty directory is passed here; no existing backup ACL changes.
    if os.name!='nt':raise BackupError('WINDOWS_OPERATOR_REQUIRED')
    sid=recovery.run(['powershell.exe','-NoProfile','-Command','[Security.Principal.WindowsIdentity]::GetCurrent().User.Value']).strip()
    recovery.run(['icacls.exe',str(path),'/inheritance:r','/grant:r','*'+sid+':(OI)(CI)F','*S-1-5-18:(OI)(CI)F'])


def require_private_acl(path):
    if os.name!='nt':raise BackupError('WINDOWS_OPERATOR_REQUIRED')
    # Operator, SYSTEM, local Administrators and trusted OWNER RIGHTS only.
    # Reject all unprivileged/broad readers; never emit secret file contents.
    script="""$ErrorActionPreference='Stop';$s=[Security.Principal.WindowsIdentity]::GetCurrent().User.Value;
$p=$env:ISHCHI_BACKUP_ACL_PATH;if([IO.Directory]::Exists($p)){$a=[IO.Directory]::GetAccessControl($p)}else{$a=[IO.File]::GetAccessControl($p)};
$trusted=@($s,'S-1-5-18','S-1-5-32-544');$owner=$a.GetOwner([Security.Principal.SecurityIdentifier]).Value;if($owner -notin $trusted){exit 9};
foreach($r in $a.Access){if($r.AccessControlType -eq 'Allow' -and $r.IdentityReference.Translate([Security.Principal.SecurityIdentifier]).Value -notin ($trusted+@('S-1-3-4'))){exit 9}};exit 0"""
    result=subprocess.run(['powershell.exe','-NoProfile','-Command',script],env={**os.environ,'ISHCHI_BACKUP_ACL_PATH':str(path)},capture_output=True,timeout=15)
    if result.returncode:raise BackupError('RESTRICTED_OPERATOR_ACL_REQUIRED')


def signed(payload,identity):
    secret_line=next(line.strip() for line in identity.read_bytes().splitlines() if line.startswith(b'AGE-SECRET-KEY-'))
    key=hashlib.sha256(b'ISHCHI local backup manifest v1\0'+secret_line).digest()
    return {'payload':payload,'hmac':hmac.new(key,canonical(payload),hashlib.sha256).hexdigest()}

def authenticate(document,identity):
    expected=signed(document['payload'],identity)['hmac']
    if not hmac.compare_digest(expected,document.get('hmac','')):raise BackupError('MANIFEST_AUTHENTICATION_FAILED')
    return document['payload']


def ledger_state(connection,media):
    return {
        'account_tombstones':[str(r[0]) for r in connection.execute("SELECT id FROM accounts_user WHERE is_anonymized OR account_status='DELETED' ORDER BY id")],
        'deletion_audit_ids':[str(r[0]) for r in connection.execute('SELECT user_id FROM accounts_deletion_audit ORDER BY user_id')],
        'pending_media_erasure':[r[0] for r in connection.execute("SELECT name FROM common_mediadeletiontask WHERE completed_at IS NULL AND name<>'' ORDER BY name")],
        'erasure_outbox':[(str(r[0]),str(r[1]),str(r[2])) for r in connection.execute('SELECT id,updated_at,completed_at FROM common_mediadeletiontask ORDER BY id')],
        'allowed_media':media,
    }

def require_fresh_ledger(ledger,current):
    # A timestamp or an old backup's ledger is never sufficient. A quiet CURRENT
    # authoritative snapshot is mandatory before recovery traffic. If unavailable,
    # recovery stays offline; re-export via the approved manual checkpoint.
    if canonical(ledger.get('state'))!=canonical(current):raise BackupError('ERASURE_LEDGER_REFRESH_REQUIRED')


def verify_archive_set(folder,identity,verify_dump,*,allow_unpublished=False):
    complete=folder/'COMPLETE.json'
    if not complete.is_file() and not allow_unpublished:raise BackupError('INCOMPLETE_BACKUP')
    manifest_path=folder/'manifest.json.age'
    if complete.is_file():
        marker=json.loads(complete.read_text(encoding='utf-8'))
        if checksum(manifest_path)!=marker['manifest_sha256']:raise BackupError('CORRUPT_MANIFEST')
    manifest=authenticate(json.loads(recovery.decrypt(manifest_path,identity)),identity)
    if set(manifest['archives'])!={'postgres.dump.age','media.tar.age'}:raise BackupError('INVALID_ARCHIVE_SET')
    for name,entry in manifest['archives'].items():
        file=folder/name
        if file.is_symlink() or file.stat().st_size!=entry['bytes'] or checksum(file)!=entry['sha256']:raise BackupError('CORRUPT_ARCHIVE')
    dump=recovery.decrypt(folder/'postgres.dump.age',identity)
    if not dump.startswith(b'PGDMP'):raise BackupError('INVALID_POSTGRES_ARCHIVE')
    verify_dump(dump)  # pg_restore --list, no database connection/restore.
    inventory=[]
    with tarfile.open(fileobj=io.BytesIO(recovery.decrypt(folder/'media.tar.age',identity)),mode='r:') as archive:
        seen=set()
        for member in archive:
            name=PurePosixPath(member.name)
            if any(c in member.name for c in ("\\",":","\0")):raise BackupError("UNSAFE_MEDIA_ARCHIVE")
            if name.is_absolute() or '..' in name.parts or not name.parts or name.parts[0]!='media' or member.issym() or member.islnk() or member.name in seen:raise BackupError('UNSAFE_MEDIA_ARCHIVE')
            seen.add(member.name)
            if member.isfile():inventory.append({'name':'/'.join(name.parts[1:]),'sha256':hashlib.sha256(archive.extractfile(member).read()).hexdigest()})
            elif not member.isdir():raise BackupError('UNSUPPORTED_MEDIA_ENTRY')
    if sorted(inventory,key=lambda x:x['name'])!=manifest['media']:raise BackupError('MEDIA_INVENTORY_MISMATCH')
    ledger_path=Path(manifest['ledger']['path'])
    if ledger_path.is_symlink() or not ledger_path.name.startswith('erasure-ledger-scheduled-') or ledger_path.parent.resolve()!=RECOVERY.resolve() or checksum(ledger_path)!=manifest['ledger']['sha256']:raise BackupError('INDEPENDENT_LEDGER_INVALID')
    ledger=authenticate(json.loads(recovery.decrypt(ledger_path,identity)),identity)
    require_fresh_ledger(ledger,manifest['erasure_state'])  # Checkpoint integrity only.
    return manifest  # Future recovery MUST also compare against a fresh live state.


def cleanup_partials(folder):
    # Never enumerate/delete published backups. Only this run's three known
    # temporary ciphertext files; completed files and unrelated paths stay intact.
    for name in ('postgres.dump.age.partial','media.tar.age.partial','manifest.json.age.partial','COMPLETE.json.partial'):
        path=folder/name
        if path.is_file() and not path.is_symlink():path.unlink()


class Runner:
    def __init__(self):self.deadline=time.monotonic()+MAX_SECONDS;self.paused=False
    def call(self,command,**kwargs):
        remaining=self.deadline-time.monotonic()
        if remaining<=0:raise BackupError('BACKUP_DEADLINE_EXCEEDED')
        return recovery.run(command,timeout=min(60,remaining),**kwargs)
    def media(self):return json.loads(self.call(recovery.DC+['run','--rm','-T','--no-deps','backend','python','-c',MEDIA_CODE]))
    def resume(self):
        # Independent bounded recovery budget; backup timeout cannot skip this.
        for command in (recovery.DC+['start','backend'],recovery.DC+['up','-d','--no-deps','--force-recreate','gateway']):
            try:recovery.run(command,timeout=60)
            except Exception:pass  # Still attempt the other service and readiness.
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        end=time.monotonic()+45
        while time.monotonic()<end:
            try:
                with opener.open('http://127.0.0.1:8080/api/v1/health/ready/',timeout=2) as response:
                    if response.status==200:return
            except OSError:pass
            time.sleep(.5)
        raise BackupError('APPLICATION_READINESS_FAILED')

    def execute(self,doc):
        recipient=authorize(doc,load_approval(PRIVATE/'work-db-authorization.json'),load_approval(PRIVATE/'work-redis-authorization.json'))
        if (expires(doc,datetime.now(timezone.utc))-datetime.now(timezone.utc)).total_seconds()<MAX_SECONDS+300:
            raise ApprovalRequired('RENEWAL_REQUIRED_FOR_FULL_BACKUP_WINDOW')
        if any(v for k,v in os.environ.items() if k.startswith('PG')):raise BackupError('LIBPQ_OVERRIDES_REFUSED')
        identity=RECOVERY/'identity.agekey'
        for path in (RECOVERY,identity,APPROVAL,PRIVATE/'local_migration_password'):require_private_acl(path)
        if (not identity.is_file() or identity.is_symlink() or not BACKUPS.is_dir()
                or BACKUPS.is_symlink() or BACKUPS.is_junction() or RECOVERY.is_symlink() or RECOVERY.is_junction()):raise BackupError('RECOVERY_STORAGE_UNAVAILABLE')
        if self.call([str(recovery.TOOLS/'age.exe'),'--version']).strip()!='v1.3.2':raise BackupError('AGE_VERSION_MISMATCH')
        if self.call([str(recovery.TOOLS/'age-keygen.exe'),'-y',str(identity)]).strip()!=recipient:raise BackupError('RECIPIENT_MISMATCH')
        # Existing bounded verifier authenticates up to 256 MiB per archive.
        if shutil.disk_usage(BACKUPS).free<1024**3:raise BackupError('INSUFFICIENT_BACKUP_STORAGE')
        self.call(['docker','--context','desktop-linux','info','--format','{{.OSType}}'])
        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:8080/api/v1/health/ready/',timeout=5) as response:
            if response.status!=200:raise BackupError('APPLICATION_NOT_READY')
        if (RECOVERY/'backup-resume-required.json').exists():raise BackupError('INTERRUPTED_BACKUP_REQUIRES_RESUME')
        identifier=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+secrets.token_hex(4)
        folder=BACKUPS/identifier;folder.mkdir(exist_ok=False);restrict_new_directory(folder)
        ledger_path=RECOVERY/('erasure-ledger-scheduled-'+identifier+'.json.age')
        marker=RECOVERY/'backup-resume-required.json'
        if marker.exists():raise BackupError('INTERRUPTED_BACKUP_REQUIRES_RESUME')
        source=None
        try:
            marker.write_text(json.dumps({'run':identifier,'action':'Resume backend and recreate gateway; verify readiness before backup retry.'}),encoding='utf-8')
            self.paused=True  # Set BEFORE stop: partial stop failures still resume.
            self.call(recovery.DC+['stop','-t','30','gateway','backend'])
            import psycopg
            source=psycopg.connect(host='127.0.0.1',port=55432,dbname='ishchi_marketplace_local',user='ishchi_local_migrator',password=(PRIVATE/'local_migration_password').read_text().strip(),sslmode='disable',connect_timeout=5,autocommit=True)
            source.execute('SET ROLE ishchi_local_owner');source.execute('SET default_transaction_read_only=on');source.execute("SET statement_timeout='60s'")
            if source.execute('SELECT current_database(),session_user,current_user').fetchone()!=('ishchi_marketplace_local','ishchi_local_migrator','ishchi_local_owner'):raise BackupError('SOURCE_IDENTITY_MISMATCH')
            key=secrets.token_bytes(32);before=recovery.fingerprint(source,key);media=self.media()
            state=ledger_state(source,media);checkpoint=datetime.now(timezone.utc).isoformat()
            ledger={'checkpoint':checkpoint,'state':state,'coverage':'CURRENT quiet checkpoint only; revalidate against authoritative live source after erasures and before recovery traffic.'}
            recovery.encrypt_json(signed(ledger,identity),ledger_path,recipient)
            image=__import__('yaml').safe_load((ROOT/'deploy/compose.local.yml').read_text())['x-pg']['image']
            client=['docker','--context','desktop-linux','run','--rm','--network','ishchi-local_work','--read-only','--cap-drop','ALL','--security-opt','no-new-privileges:true','--mount','type=bind,source='+str(PRIVATE/'local_migration_password')+',target=/run/secrets/password,readonly',image]
            dump='export PGPASSWORD="$(tr -d \'\\r\\n\' < /run/secrets/password)"; exec pg_dump -h postgres-work -p 5432 -U ishchi_local_migrator --role=ishchi_local_owner -d ishchi_marketplace_local -Fc --no-owner --no-acl'
            recovery.stream_encrypt(client+['sh','-ec',dump],folder/'postgres.dump.age',recipient)
            recovery.stream_encrypt(recovery.DC+['run','--rm','-T','--no-deps','backend','python','-c',TAR_CODE],folder/'media.tar.age',recipient)
            if self.media()!=media or recovery.fingerprint(source,key)!=before:raise BackupError('CHECKPOINT_CHANGED')
            manifest={'checkpoint':checkpoint,'source':SOURCE,'media':media,'erasure_state':state,'archives':{name:{'bytes':(folder/name).stat().st_size,'sha256':checksum(folder/name)} for name in ['postgres.dump.age','media.tar.age']},'ledger':{'path':str(ledger_path),'sha256':checksum(ledger_path)},'retention_days':30,'automatic_deletion':False,'offline_key_copy':'OWNER_ACTION_REQUIRED'}
            recovery.encrypt_json(signed(manifest,identity),folder/'manifest.json.age',recipient)
            verify_archive_set(folder,identity,lambda data:self.call(['docker','--context','desktop-linux','run','--rm','-i','--network','none','--read-only',image,'pg_restore','--list'],data=data,binary=True),allow_unpublished=True)
            temporary=folder/'COMPLETE.json.partial'
            with temporary.open('x',encoding='utf-8') as output:
                output.write(json.dumps({'manifest_sha256':checksum(folder/'manifest.json.age'),'status':'PASS','restore':'NOT RUN'}))
                output.flush();os.fsync(output.fileno())
            temporary.rename(folder/'COMPLETE.json')
            return {'status':'PASS','run':identifier,'restore':'NOT RUN','ciphertext_integrity':'PASS','retention_deletion':'DISABLED'}
        except BaseException:
            # COMPLETE is published only after authentication and structural checks.
            if not (folder/'COMPLETE.json').exists():
                (folder/'FAILED.json').write_text('{"status":"FAIL"}',encoding='utf-8')
            cleanup_partials(folder)
            partial=ledger_path.with_suffix(ledger_path.suffix+'.partial')
            if partial.is_file() and not partial.is_symlink():partial.unlink()
            raise
        finally:
            try:
                if source:source.close()
            finally:
                if self.paused:
                    self.resume()
                    marker.unlink(missing_ok=True)  # Only this run's recovery marker.


def persist_status(report,code):
    if not RECOVERY.is_dir():return
    logs=RECOVERY/'backup-logs';logs.mkdir(exist_ok=True)
    name=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+secrets.token_hex(4)
    text=json.dumps({**report,'finished_at':datetime.now(timezone.utc).isoformat(),'exit_code':code})
    event=logs/(name+'.partial');event.write_text(text,encoding='utf-8');event.rename(logs/(name+'.json'))
    temporary=RECOVERY/('backup-status-'+secrets.token_hex(4)+'.partial')
    temporary.write_text(text,encoding='utf-8');temporary.replace(RECOVERY/'scheduled-backup-status.json')

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    actions=parser.add_mutually_exclusive_group()
    actions.add_argument('--execute',action='store_true')
    actions.add_argument('--resume-only',action='store_true',help='Resume an interrupted approved checkpoint only; no backup/restore.')
    args=parser.parse_args(argv)
    if not args.execute and not args.resume_only:
        print('PREPARED ONLY: daily 20:00 Asia/Tashkent; no connection/backup/restore/scheduler installation. Separate owner approval required.')
        return 0
    report={'status':'FAIL'};code=1
    try:
        # Approval validation happens before directory/lock/service operations.
        runtime=load_approval(PRIVATE/'work-db-authorization.json');redis_doc=load_approval(PRIVATE/'work-redis-authorization.json')
        if args.resume_only:
            authorize_runtime(runtime,redis_doc)
            require_private_acl(RECOVERY)
            with exclusive_lock(RECOVERY/'scheduled-backup.lock'):
                marker=RECOVERY/'backup-resume-required.json'
                if not marker.is_file() or marker.is_symlink():raise BackupError('NO_INTERRUPTED_CHECKPOINT')
                Runner().resume()
                marker.unlink()
            report={'status':'RESUMED','backup':'NOT RUN','restore':'NOT RUN'}
            persist_status(report,0)
            print(json.dumps(report));return 0
        doc=load_approval(APPROVAL)
        authorize(doc,runtime,redis_doc)
        with exclusive_lock(RECOVERY/'scheduled-backup.lock'):
            import threading,_thread
            watchdog=threading.Timer(MAX_SECONDS,_thread.interrupt_main);watchdog.daemon=True;watchdog.start()
            try:report=Runner().execute(doc)
            finally:watchdog.cancel()
        code=0
    except ApprovalRequired:report={'status':'REQUIRES APPROVAL','reason':'RENEWAL_OR_EXACT_BACKUP_SCOPE_REQUIRED'};code=3
    except Overlap:report={'status':'SKIPPED','reason':'BACKUP_ALREADY_RUNNING'};code=4
    except (Exception,KeyboardInterrupt) as exc:
        reason=str(exc) if isinstance(exc,BackupError) else 'CHECK_APPLICATION_READINESS_AND_OPERATOR_CONFIGURATION'
        report={'status':'FAIL','reason':reason,'error_type':type(exc).__name__};code=1
    # Fixed metadata only: no child output, credentials, storage keys or row data.
    try:persist_status(report,code)
    except OSError:report={'status':'FAIL','reason':'STATUS_LOG_PERSISTENCE_FAILED'};code=1
    print(json.dumps(report))
    return code

if __name__=='__main__':raise SystemExit(main())
