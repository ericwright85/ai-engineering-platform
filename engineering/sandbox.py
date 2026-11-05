"""Fixed test command inside a resource-limited Docker container, never on the host."""
import subprocess
from pathlib import Path

IMAGE = 'python:3.12-slim'

def command(repository):
    root = Path(repository).resolve(strict=True)
    if not root.is_dir() or any(p.is_symlink() for p in root.rglob('*')):
        raise ValueError('Sandbox input must be a directory without symlinks')
    return ['docker','run','--rm','--pull=never','--network=none','--read-only',
            '--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=64',
            '--memory=256m','--cpus=1','--user=65534:65534',
            '--tmpfs=/tmp:rw,noexec,nosuid,size=32m',
            '--mount',f'type=bind,src={root},dst=/repo,readonly',
            '--workdir=/repo','--env=PYTHONDONTWRITEBYTECODE=1',IMAGE,
            'python','-I','-m','unittest','discover','-s','tests','-v']

def run(store, task_id, repository):
    if store.get(task_id)['state'] != 'approved':
        raise ValueError('Human approval required before sandbox execution')
    # No shell, arbitrary command, secret/environment forwarding or Docker socket mount.
    # Output is bounded in the container before reaching the host subprocess pipe.
    argv = command(repository)
    script = 'import subprocess,sys; p=subprocess.run(sys.argv[1:],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=30); sys.stdout.buffer.write(p.stdout[:65536]); sys.exit(p.returncode)'
    # Inner wrapper's PIPE could grow; Docker memory cap bounds it and outer timeout bounds lifetime.
    argv = argv[:argv.index(IMAGE)+1] + ['python','-I','-c',script,'python','-I','-m','unittest','discover','-s','tests','-v']
    try:
        completed = subprocess.run(argv, capture_output=True, timeout=45, check=False)
        result = {'exit_code':completed.returncode,'output':completed.stdout[:65536].decode(errors='replace'),'error':completed.stderr[:4096].decode(errors='replace')}
    except subprocess.TimeoutExpired:
        result = {'exit_code':124,'output':'','error':'Sandbox timeout; container inner timeout is 30 seconds'}
    store.event(task_id,'sandbox.completed',result)
    store.db.commit()
    return result
