"""Owner-approved encrypted local checkpoint and NEW isolated restore verification.

No working data mutation. Default is an offline description. No archive retention
deletion, volume deletion, working restore, existing target adoption or key output.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import hmac
import io
import json
import os
from pathlib import Path, PurePosixPath
import secrets
import socket
import subprocess
import tarfile
import time
import urllib.request
import yaml

ROOT = Path(__file__).resolve().parents[1]
PRIVATE = Path(r"C:\Users\user\.codex\ishchi-local-private")
RECOVERY = PRIVATE / "recovery"
TOOLS = PRIVATE / "tools/age-v1.3.2"
BACKUPS = Path(r"D:\Ishchi-backups")
SANDBOX = Path(r"D:\Ishchi-restore-sandbox")
DC = ["docker", "--context", "desktop-linux", "compose", "--env-file", "deploy/.env.local", "-f", "deploy/compose.local.yml", "--profile", "work"]
RESTORE = dict(host="127.0.0.1", port="55434", dbname="ishchi_marketplace_restore_local", user="ishchi_local_restore")


def require_approval():
    doc = json.loads((RECOVERY / "recovery-authorization.json").read_text())
    expected = {"source_database":"ishchi_marketplace_local", "source_port":55432,
        "destination":str(BACKUPS), "sandbox":str(SANDBOX), "restore_target":RESTORE, "retention_days":30}
    if doc['plan'] != expected or not doc['approved_by'].strip() or datetime.fromisoformat(doc['expires_at'].replace('Z','+00:00')) <= datetime.now(timezone.utc):
        raise ValueError('Exact unexpired recovery approval required')
    required={'new_age_identity','encrypted_pg_media_backup','new_isolated_restore_cluster','restore_empty_target','checkpoint_reconciliation','verify_restore'}
    if not required <= set(doc.get('operations', [])):
        raise ValueError('Missing separately approved recovery operation scope')
    if any(value for key,value in os.environ.items() if key.startswith('PG')):
        raise ValueError('Clear libpq overrides')


def run(command, *, data=None, binary=False, timeout=60):
    result = subprocess.run(command,input=data,capture_output=True,text=not binary,cwd=ROOT,timeout=timeout)
    if result.returncode:
        raise RuntimeError('Recovery subprocess failed; no arbitrary child output emitted')
    return result.stdout


def stream_encrypt(command, destination, recipient):
    """Never persist plaintext; require producer AND age success before publication."""
    if destination.exists():
        raise ValueError('Refusing archive overwrite')
    partial = destination.with_suffix(destination.suffix + '.partial')
    with partial.open('xb') as output:
        producer = subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=ROOT)
        encryptor = subprocess.Popen([str(TOOLS/'age.exe'),'-r',recipient],stdin=producer.stdout,stdout=output,stderr=subprocess.PIPE)
        producer.stdout.close()
        producer.stdout = None  # Windows communicate must not read the closed pipe.
        try:
            encryptor.communicate(timeout=90)
            producer.communicate(timeout=90)
        except BaseException:
            for process in (producer,encryptor):
                if process.poll() is None: process.kill()
                process.wait()
            raise
        if producer.returncode or encryptor.returncode:
            raise RuntimeError('Encryption/producer failure; unpublished ciphertext retained as .partial')
        output.flush(); os.fsync(output.fileno())
    if destination.exists():
        raise ValueError('Archive target collision')
    partial.rename(destination)


def encrypt_json(document, destination, recipient):
    if destination.exists(): raise ValueError('Refusing ledger/manifest overwrite')
    partial=destination.with_suffix(destination.suffix+'.partial')
    with partial.open('xb') as output:
        result = subprocess.run([str(TOOLS/'age.exe'),'-r',recipient],input=json.dumps(document,sort_keys=True).encode(),stdout=output,stderr=subprocess.PIPE,timeout=60)
        if result.returncode: raise RuntimeError('Metadata encryption failed')
        output.flush(); os.fsync(output.fileno())
    partial.rename(destination)


def decrypt(path, identity):
    # Bounded local MVP verifier: authenticate the WHOLE archive before consuming it.
    if path.stat().st_size>256*1024*1024:raise RuntimeError('Archive exceeds 256 MiB local verification limit')
    return run([str(TOOLS/'age.exe'),'-d','-i',str(identity),str(path)],binary=True)


def fingerprint(connection, key):
    from psycopg import sql
    tables = connection.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename").fetchall()
    rows = {}; digests = {}
    for (name,) in tables:
        values = connection.execute(sql.SQL('SELECT to_jsonb(t) FROM public.{} AS t ORDER BY to_jsonb(t)::text').format(sql.Identifier(name))).fetchall()
        rows[name]=len(values)
        digests[name]=hmac.new(key,json.dumps(values,sort_keys=True,default=str).encode(),hashlib.sha256).hexdigest()
    schema = {}
    for label, query in (
        ('constraints',"SELECT conrelid::regclass::text,conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE connamespace='public'::regnamespace ORDER BY 1,2"),
        ('triggers',"SELECT c.relname,t.tgname,pg_get_triggerdef(t.oid) FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid WHERE c.relnamespace='public'::regnamespace AND NOT t.tgisinternal ORDER BY 1,2"),
        ('functions',"SELECT pg_get_functiondef(oid) FROM pg_proc WHERE pronamespace='public'::regnamespace ORDER BY proname"),
        ('indexes',"SELECT indexname,indexdef FROM pg_indexes WHERE schemaname='public' ORDER BY indexname")):
        schema[label]=connection.execute(query).fetchall()
        if label=='indexes':
            schema[label]=[(name,canonical_index_definition(name,definition)) for name,definition in schema[label]]
    sequences={}
    for (name,) in connection.execute("SELECT sequencename FROM pg_sequences WHERE schemaname='public' ORDER BY sequencename"):
        sequences[name]=connection.execute(sql.SQL('SELECT last_value,is_called FROM public.{}').format(sql.Identifier(name))).fetchone()
    return {'rows':rows,'digests':digests,'schema':schema,'sequences':sequences}


def canonical_index_definition(name, definition):
    # pg_dump/reparse distributes an array cast over these exact two constants.
    # Normalize ONLY this known equivalent form on the two active-request indexes.
    old="WHERE ((status)::text = ANY ((ARRAY['PENDING'::character varying, 'ACCEPTED'::character varying])::text[]))"
    new="WHERE ((status)::text = ANY (ARRAY[('PENDING'::character varying)::text, ('ACCEPTED'::character varying)::text]))"
    if name in {'uq_active_order_worker_application','uq_active_order_worker_invitation'} and definition.endswith(old):
        return definition[:-len(old)]+new
    return definition


def verify_erasure_reconciliation(connection, ledger, media_inventory):
    """Independent CURRENT ledger gates restored data; never permit resurrection."""
    tombstones=set(ledger['account_tombstones'])|set(ledger['deletion_audit_ids'])
    with connection.cursor() as cursor:
        for user_id in tombstones:
            cursor.execute('SELECT is_anonymized,phone_number,password,is_active FROM accounts_user WHERE id=%s',[user_id])
            row=cursor.fetchone()
            if row and (not row[0] or row[1] is not None or not row[2].startswith('!') or row[3]):
                raise RuntimeError('Restore would resurrect erased account; traffic remains blocked')
    forbidden=set(ledger['pending_media_erasure'])
    allowed={entry['name']:entry['sha256'] for entry in ledger['allowed_media']}
    if any(entry['name'] in forbidden or allowed.get(entry['name'])!=entry['sha256'] for entry in media_inventory):
        raise RuntimeError('Media conflicts with current independent erasure ledger; traffic remains blocked')
    return len(tombstones),len(forbidden)


def export_current_ledger():
    """Explicit manual checkpoint after erasure; separate encrypted append-only file.

    Uses the non-owner app login for read-only SELECT; no dump, restore or deletion.
    Still requires an owner-approved recovery/ledger scope and currentness checks.
    """
    require_approval()
    import psycopg
    identity=RECOVERY/'identity.agekey'
    recipient=run([str(TOOLS/'age-keygen.exe'),'-y',str(identity)]).strip()
    paused=False
    try:
        run(DC+['stop','gateway','backend']);paused=True
        code="""import json,hashlib;from pathlib import Path
root=Path('/app/media');out=[]
for p in sorted(root.rglob('*')):
 if p.is_symlink():raise RuntimeError('Media link refused')
 if p.is_file():out.append({'name':p.relative_to(root).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
print(json.dumps(out))
"""
        media=json.loads(run(DC+['run','--rm','-T','--no-deps','backend','python','-c',code]))
        with psycopg.connect(host='127.0.0.1',port=55432,dbname='ishchi_marketplace_local',user='ishchi_local_app',
            password=(PRIVATE/'work_pg_password').read_text().strip(),sslmode='disable',connect_timeout=5) as connection:
            connection.execute('SET TRANSACTION READ ONLY')
            ledger={'checkpoint':datetime.now(timezone.utc).isoformat(),
                'account_tombstones':[str(row[0]) for row in connection.execute("SELECT id FROM accounts_user WHERE is_anonymized OR account_status='DELETED' ORDER BY id")],
                'deletion_audit_ids':[str(row[0]) for row in connection.execute('SELECT user_id FROM accounts_deletion_audit ORDER BY user_id')],
                'pending_media_erasure':[row[0] for row in connection.execute("SELECT name FROM common_mediadeletiontask WHERE completed_at IS NULL AND name<>'' ORDER BY name")],
                'allowed_media':media,'coverage':'Quiet authoritative checkpoint; export again after subsequent deletion and before recovery traffic'}
        destination=RECOVERY/('erasure-ledger-current-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+secrets.token_hex(4)+'.json.age')
        encrypt_json(ledger,destination,recipient)
        if json.loads(decrypt(destination,identity))!=ledger:raise RuntimeError('Independent ledger verification failed')
        latest=RECOVERY/'latest-erasure-ledger.json'
        temporary=latest.with_suffix('.partial')
        with temporary.open('x',encoding='utf-8',newline='\n') as output:
            output.write(json.dumps({'ledger':str(destination),'checkpoint':ledger['checkpoint'],'sha256':hashlib.sha256(destination.read_bytes()).hexdigest()},indent=2)+'\n')
            output.flush();os.fsync(output.fileno())
        temporary.replace(latest)
        print('PASS: fresh independent encrypted erasure ledger exported/authenticated; no database/media mutation.')
    finally:
        if paused:run(DC+['start','backend','gateway'])


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--export-ledger',action='store_true')
    args=parser.parse_args(argv)
    if args.export_ledger:
        export_current_ledger()
        return
    if not args.execute:
        print('DRY RUN: no key, connection, archive, provisioning or restore')
        return
    require_approval()
    import psycopg
    from psycopg import sql
    if SANDBOX.exists(): raise ValueError('Restore sandbox already exists; no adoption or overwrite')
    with socket.socket() as probe: probe.bind(('127.0.0.1',55434))
    identifier=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+secrets.token_hex(4)
    destination=BACKUPS/identifier; destination.mkdir(parents=True,exist_ok=False)
    sandbox=SANDBOX/identifier; media=sandbox/'media'; media.mkdir(parents=True,exist_ok=False)
    identity=RECOVERY/'identity.agekey'
    if identity.exists(): raise ValueError('Refusing recovery identity replacement')
    run([str(TOOLS/'age-keygen.exe'),'-o',str(identity)])
    recipient=run([str(TOOLS/'age-keygen.exe'),'-y',str(identity)]).strip()
    if not recipient.startswith('age1'): raise ValueError('Unexpected age recipient')
    restore_password=secrets.token_urlsafe(48); bootstrap_password=secrets.token_urlsafe(48)
    for name,value in (('restore_password',restore_password),('restore_bootstrap_password',bootstrap_password)):
        with (RECOVERY/name).open('x',encoding='utf-8',newline='\n') as output: output.write(value+'\n')
    image=yaml.safe_load((ROOT/'deploy/compose.local.yml').read_text())['x-pg']['image']
    project='ishchi-local-restore-'+identifier.lower()
    config={'name':project,'services':{'postgres-restore':{'image':image,'environment':{
        'POSTGRES_USER':'ishchi_restore_bootstrap','POSTGRES_DB':RESTORE['dbname'],
        'POSTGRES_PASSWORD_FILE':'/run/secrets/bootstrap_password','POSTGRES_INITDB_ARGS':'--auth-host=scram-sha-256'},
        'ports':['127.0.0.1:55434:5432'],'volumes':['pg-restore:/var/lib/postgresql'],
        'secrets':[{'source':'bootstrap','target':'bootstrap_password'},{'source':'restore','target':'restore_password'}]}},
        'volumes':{'pg-restore':{}},'secrets':{'bootstrap':{'file':str(RECOVERY/'restore_bootstrap_password')},'restore':{'file':str(RECOVERY/'restore_password')}}}
    compose=ROOT/'deploy/.local'/('restore-'+identifier+'.yml')
    compose.write_text(yaml.safe_dump(config))
    restore_dc=['docker','--context','desktop-linux','compose','-f',str(compose)]
    report={'started_at':datetime.now(timezone.utc).isoformat(),'identifier':identifier,'retention_days':30,'automatic_deletion':False,
        'destination':str(destination),'sandbox':str(sandbox),'restore_project':project,'restore_target':RESTORE,
        'status':'NOT VERIFIED','working_restore_performed':False,'independent_offline_key_copy':'OWNER ACTION REQUIRED'}
    paused=False; source=None; clone=None
    try:
        run(DC+['stop','gateway','backend']); paused=True
        source=psycopg.connect(host='127.0.0.1',port=55432,dbname='ishchi_marketplace_local',user='ishchi_local_migrator',
            password=(PRIVATE/'local_migration_password').read_text().strip(),sslmode='disable',connect_timeout=5,autocommit=True)
        source.execute('SET ROLE ishchi_local_owner')
        source.execute('SET default_transaction_read_only=on')
        key=secrets.token_bytes(32)
        before=fingerprint(source,key)
        media_code="""import os,json,hashlib;from pathlib import Path
root=Path('/app/media'); result=[]
for file in sorted(root.rglob('*')):
 if file.is_symlink(): raise RuntimeError('Media symlink refused')
 if file.is_file(): result.append({'name':file.relative_to(root).as_posix(),'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
print(json.dumps(result))
"""
        source_media=json.loads(run(DC+['run','--rm','-T','--no-deps','backend','python','-c',media_code]))
        ledger={'checkpoint':datetime.now(timezone.utc).isoformat(),'source':'quiet working DB + media checkpoint; independent from archives',
            'account_tombstones':[str(row[0]) for row in source.execute('SELECT id FROM accounts_user WHERE is_anonymized OR account_status=\'DELETED\' ORDER BY id')],
            'deletion_audit_ids':[str(row[0]) for row in source.execute('SELECT user_id FROM accounts_deletion_audit ORDER BY user_id')],
            'pending_media_erasure':[row[0] for row in source.execute("SELECT name FROM common_mediadeletiontask WHERE completed_at IS NULL AND name<>'' ORDER BY name")],
            'allowed_media':source_media,'coverage':'Complete for this paused checkpoint only; refresh independently after subsequent erasures and before recovery traffic'}
        ledger_path=RECOVERY/('erasure-ledger-'+identifier+'.json.age')
        encrypt_json(ledger,ledger_path,recipient)
        db_archive=destination/'postgres.dump.age'; media_archive=destination/'media.tar.age'
        client=['docker','--context','desktop-linux','run','--rm','--network','ishchi-local_work','--read-only','--cap-drop','ALL',
            '--security-opt','no-new-privileges:true','--mount','type=bind,source='+str(PRIVATE/'local_migration_password')+',target=/run/secrets/password,readonly',image]
        dump="export PGPASSWORD=\"$(cat /run/secrets/password)\"; exec pg_dump -h postgres-work -p 5432 -U ishchi_local_migrator --role=ishchi_local_owner -d ishchi_marketplace_local -Fc --no-owner --no-acl"
        stream_encrypt(client+['sh','-ec',dump],db_archive,recipient)
        tar_code="""import tarfile;from pathlib import Path;import sys
root=Path('/app/media')
if any(p.is_symlink() for p in root.rglob('*')):raise RuntimeError('Media links refused')
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|') as archive:archive.add(root,arcname='media')
"""
        stream_encrypt(DC+['run','--rm','-T','--no-deps','backend','python','-c',tar_code],media_archive,recipient)
        manifest={'checkpoint':ledger['checkpoint'],'migration_rows':before['rows'].get('django_migrations'),
            'archives':{p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in (db_archive,media_archive)},
            'independent_ledger':str(ledger_path),'age_version':'v1.3.2','retention_days':30,'no_automatic_deletion':True}
        encrypt_json(manifest,destination/'manifest.json.age',recipient)
        if json.loads(decrypt(destination/'manifest.json.age',identity)) != manifest:raise RuntimeError('Manifest verification failed')
        for path in (db_archive,media_archive):
            if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['archives'][path.name]['sha256']:raise RuntimeError('Ciphertext integrity mismatch')
        database_plain=decrypt(db_archive,identity)
        media_plain=decrypt(media_archive,identity)
        restored_ledger=json.loads(decrypt(ledger_path,identity))
        run(restore_dc+['up','-d'])
        deadline=time.monotonic()+30
        while True:
            try:
                clone=psycopg.connect(**{**RESTORE,'user':'ishchi_restore_bootstrap'},password=bootstrap_password,sslmode='disable',connect_timeout=2,autocommit=True)
                break
            except psycopg.OperationalError:
                if time.monotonic()>deadline:raise RuntimeError('New restore PostgreSQL did not become ready') from None
                time.sleep(.4)
        if clone.execute('SELECT current_database(),session_user').fetchone()!=(RESTORE['dbname'],'ishchi_restore_bootstrap'):raise ValueError('Wrong restore identity')
        if clone.execute("SELECT count(*) FROM pg_tables WHERE schemaname='public'").fetchone()[0]!=0:raise ValueError('Restore database is not empty')
        verifier=clone.pgconn.encrypt_password(restore_password.encode(),RESTORE['user'].encode(),b'scram-sha-256').decode()
        clone.execute(sql.SQL('CREATE ROLE ishchi_local_restore LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD {}').format(sql.Literal(verifier)))
        clone.execute('ALTER DATABASE ishchi_marketplace_restore_local OWNER TO ishchi_local_restore')
        clone.execute('REVOKE ALL ON DATABASE ishchi_marketplace_restore_local FROM PUBLIC')
        clone.execute('REVOKE CONNECT ON DATABASE postgres FROM PUBLIC')
        clone.execute('REVOKE CONNECT ON DATABASE template1 FROM PUBLIC')
        clone.close();clone=None
        restore_cmd='export PGPASSWORD="$(tr -d \'\\r\\n\' < /run/secrets/restore_password)"; exec pg_restore -h 127.0.0.1 -U ishchi_local_restore -d ishchi_marketplace_restore_local --no-owner --no-acl --exit-on-error --single-transaction'
        run(restore_dc+['exec','-T','postgres-restore','sh','-ec',restore_cmd],data=database_plain,binary=True)
        database_plain=None
        clone=psycopg.connect(**RESTORE,password=restore_password,sslmode='disable',connect_timeout=5,autocommit=True)
        restored=fingerprint(clone,key)
        if restored!=before:raise RuntimeError('Restored rows/schema/triggers/sequences do not match checkpoint')
        with tarfile.open(fileobj=io.BytesIO(media_plain),mode='r:') as archive:
            for member in archive:
                name=PurePosixPath(member.name)
                if name.is_absolute() or '..' in name.parts or not name.parts or name.parts[0]!='media' or member.issym() or member.islnk():raise ValueError('Unsafe media archive member')
                relative=Path(*name.parts[1:]); target=media/relative
                if member.isdir():target.mkdir(parents=True,exist_ok=True)
                elif member.isfile():
                    target.parent.mkdir(parents=True,exist_ok=True)
                    with target.open('xb') as output:output.write(archive.extractfile(member).read())
                else:raise ValueError('Unsupported media archive entry')
        media_plain=None
        restored_media=[{'name':p.relative_to(media).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(media.rglob('*')) if p.is_file()]
        if restored_media!=source_media:raise RuntimeError('Restored media mismatch')
        tombstone_count,pending_count=verify_erasure_reconciliation(clone,restored_ledger,restored_media)
        if fingerprint(source,key)!=before:raise RuntimeError('Working database changed during checkpoint')
        report.update(status='PASS',backup_encryption='PASS',authenticated_decryption='PASS',restore='PASS',
            rows=before['rows'],media_files=len(restored_media),schema_constraints_triggers_sequences='PASS',
            checkpoint_erasure_reconciliation='PASS',account_tombstones_checked=tombstone_count,pending_media_erasure=pending_count,
            erasure_scope='Paused checkpoint only; no nonempty erasure replay occurred',
            future_recovery_gate='Refresh independent erasure ledger after every subsequent deletion; absent/currentness-unproven ledger blocks traffic',
            work_data_preserved=True,restore_application_exposed=False,restore_auth_tokens='No application exposed; existing tokens/passwords must never be used to open this sandbox to traffic')
    except Exception as exc:
        report['error']=type(exc).__name__+((':sqlstate='+exc.sqlstate) if getattr(exc,'sqlstate',None) else '')
        raise
    finally:
        for connection in (source,clone):
            if connection is not None:connection.close()
        if paused:
            run(DC+['start','backend','gateway'])
            opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
            deadline=time.monotonic()+30
            while time.monotonic()<deadline:
                try:
                    with opener.open('http://127.0.0.1:8080/api/v1/health/ready/',timeout=2) as response:
                        if response.status==200:report['work_readiness']='PASS';break
                except OSError:pass
                time.sleep(.3)
            else:report['work_readiness']='FAIL'
        report['finished_at']=datetime.now(timezone.utc).isoformat()
        (ROOT/'deploy/.local/recovery-result.json').write_text(json.dumps(report,indent=2)+'\n')
    if report.get('work_readiness')!='PASS':raise RuntimeError('Working readiness failed')
    print('PASS: real encrypted PG/media backup and authenticated isolated restore; rows/schema/media match; current checkpoint tombstones checked; working data/readiness preserved.')


if __name__=='__main__':
    main()
