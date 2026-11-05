"""Bounded read-only adapters. Never import or execute reviewed repository code."""
import json
import re
import urllib.request
from pathlib import Path

MAX_BYTES = 200_000
MAX_FILES = 50

def validate_files(files):
    if not isinstance(files, dict) or len(files) > MAX_FILES:
        raise ValueError('File budget exceeded')
    total = 0
    for name, content in files.items():
        if not isinstance(name, str) or name.startswith('/') or '..' in name.split('/') or '\\' in name:
            raise ValueError('Unsafe source path')
        if not isinstance(content, str):
            raise ValueError('Expected text')
        total += len(content.encode())
    if total > MAX_BYTES:
        raise ValueError('Input byte budget exceeded')
    return files

def fixture(path):
    p = Path(path)
    if p.stat().st_size > MAX_BYTES:
        raise ValueError('Fixture budget exceeded')
    return validate_files(json.loads(p.read_text()))

class GitHub:
    def __init__(self, token=None):
        self.token = token

    def _get(self, path):
        headers = {'Accept':'application/vnd.github+json', 'User-Agent':'educational-engineering-platform', 'X-GitHub-Api-Version':'2022-11-28'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        request = urllib.request.Request('https://api.github.com' + path, headers=headers)
        # No arbitrary URL or redirects, preventing credential forwarding to other hosts.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *args, **kwargs):
                raise ValueError('GitHub redirect refused')
        with urllib.request.build_opener(NoRedirect).open(request, timeout=20) as r:
            body = r.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError('GitHub response budget exceeded')
        return json.loads(body)

    def pull_request(self, repository, number):
        if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository) or type(number) is not int or number < 1:
            raise ValueError('Invalid PR identity')
        files = self._get(f'/repos/{repository}/pulls/{number}/files?per_page=50')
        if len(files) >= MAX_FILES:
            raise ValueError('PR may be truncated; use a smaller PR')
        if any('patch' not in f for f in files):
            raise ValueError('Binary or truncated patch is unsupported')
        # Evidence coordinates refer to patch lines, explicitly labeled in the task.
        return validate_files({f['filename']:f['patch'] for f in files})
