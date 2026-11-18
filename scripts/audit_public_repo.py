"""Read-only index/history scan. This is a guardrail, not a claim of perfect secret detection."""
import re
import subprocess
from pathlib import Path
from dotenv import dotenv_values

BLOCKED=('data/raw/','data/processed/','data/annotations/','outputs/','models/','.venv/','postgres-data/','pgdata/')


def git(*args):
    return subprocess.check_output(['git',*args])


def main():
    values=dotenv_values('.env') if Path('.env').exists() else {}
    known=[v for k,v in values.items() if v and len(v)>=8 and
           (k.endswith('_KEY') or k.endswith('_SECRET') or k.endswith('_PASSWORD'))]
    objects={}
    for line in git('ls-files','--stage','-z').split(b'\0'):
        if line:
            meta,name=line.split(b'\t',1);objects[(name.decode(),meta.split()[1].decode())]='index'
    for commit in git('rev-list','--all').decode().splitlines():
        for line in git('ls-tree','-r','-z',commit).split(b'\0'):
            if line:
                meta,name=line.split(b'\t',1)
                if meta.split()[1]==b'blob': objects[(name.decode(),meta.split()[2].decode())]='history'
    findings=[];seen={}
    for (name,oid),where in objects.items():
        base=Path(name).name
        if name.startswith(BLOCKED) or (base.startswith('.env') and base!='.env.example') or base.endswith(('.pem','.key','.p12','.pfx')):
            findings.append((where,name,'private_path'))
        if oid not in seen: seen[oid]=git('cat-file','blob',oid)
        data=seen[oid]
        if len(data)>1_000_000: findings.append((where,name,'large_blob'))
        text=data.decode('utf-8',errors='replace')
        if any(v in text for v in known): findings.append((where,name,'known_local_secret'))
        if re.search(r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----|sk-[A-Za-z0-9_-]{24,}',text):
            findings.append((where,name,'credential_pattern'))
    if findings:
        for finding in sorted(set(findings)): print(*finding,sep=': ')
        raise SystemExit(1)
    print(f'PASS: {len(seen)} distinct Git blobs checked across index/history; no blocked paths, large blobs, known local secrets or matched credential patterns.')
    print('Dataset/license and intentional personal metadata still require human publication review.')


if __name__=='__main__':main()
