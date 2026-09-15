#!/usr/bin/env python3
"""Acquire the locked G2 source subset without executing vendor code.

Only files named in the project lock are downloaded from its immutable dataset
revision. Size and SHA-256 checks establish repeatable input identity; license
acknowledgment records consent for this lock, not a transfer of rights.
"""
import argparse
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import tempfile
import re
import signal
import time
import uuid
import urllib.error
import urllib.request


class DownloadDeadlineExceeded(RuntimeError):
    """A whole file, including retries, exceeded its wall-clock budget."""


@contextmanager
def download_deadline(seconds):
    """Bound DNS, transfer, retry, and backoff by one wall-clock deadline.

    This Unix signal timer runs on the CLI's main thread and restores any timer
    and handler owned by its caller when the context exits.
    """
    # This CLI runs on the main thread of the supported Linux/Mac platforms.
    # The timer interrupts a stalled DNS/connect/read too; socket timeouts alone
    # do not bound a server that keeps delivering very small chunks.
    deadline = time.monotonic() + seconds
    previous_handler = signal.getsignal(signal.SIGALRM)
    def check(*unused):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise DownloadDeadlineExceeded('Model file download deadline exceeded')
        signal.setitimer(signal.ITIMER_REAL, remaining)
    signal.signal(signal.SIGALRM, check)
    previous_timer = signal.setitimer(signal.ITIMER_REAL, seconds)
    started = time.monotonic()
    try:
        yield check
        check()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        if previous_timer[0]:
            signal.setitimer(signal.ITIMER_REAL,
                            max(0.000001, previous_timer[0] - (time.monotonic() - started)),
                            previous_timer[1])


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def fetch(lock, cache, accept_noncommercial_license=False, file_timeout=600):
    """Populate and verify exactly the files described by a model lock.

    Valid cache entries require locked size and digest. Damaged entries are moved
    aside before an atomic temporary-file download; bounded retries never accept
    HTML/API errors, LFS pointers, partial data, or checksum mismatches.
    """
    if not 0 < file_timeout <= 3600:
        raise ValueError('File timeout must be positive and at most 3600 seconds')
    manifest = json.loads(lock.read_text())
    if manifest.get('repo_type') != 'dataset' or manifest.get('repo_id') != manifest.get('repository'):
        raise ValueError('Expected a locked Hugging Face dataset identity')
    if not re.fullmatch(r'[a-f0-9]{40}', manifest['revision']):
        raise ValueError('Model revision must be a full immutable commit, not main/latest')
    if manifest['license'] != 'CC-BY-NC-SA-4.0':
        raise ValueError('Unreviewed model license')
    cache.mkdir(parents=True, exist_ok=True)
    acknowledgment = cache / 'license-acknowledgment.json'
    lock_hash = sha256(lock)
    accepted = (acknowledgment.is_file() and
                json.loads(acknowledgment.read_text()).get('lock_sha256') == lock_hash)
    if not accepted and not accept_noncommercial_license:
        raise ValueError('Read model_sources/g2.lock.json and its official license. '
                         'For your own noncommercial use, pass --accept-noncommercial-license. '
                         'The author cannot accept restrictions for a future recipient.')
    if accept_noncommercial_license:
        acknowledgment.write_text(json.dumps({'license': manifest['license'],
            'lock_sha256': lock_hash, 'scope': 'Caller confirmed noncommercial use'}, indent=2) + '\n')
    base = ('https://huggingface.co/datasets/' + manifest['repository'] +
            '/resolve/' + manifest['revision'] + '/')
    results = []
    for item in manifest['files']:
        relative = Path(item['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe model path')
        path = cache / 'raw' / relative
        if path.is_symlink() or not path.resolve().is_relative_to((cache / 'raw').resolve()):
            raise ValueError('Unsafe model cache path')
        valid = (path.is_file() and path.stat().st_size == item['size'] and
                 sha256(path) == item['sha256'])
        if not valid:
            if path.exists():
                quarantine = cache / 'quarantine' / uuid.uuid4().hex / relative
                quarantine.parent.mkdir(parents=True, exist_ok=True)
                path.replace(quarantine)
                print('QUARANTINED damaged cache: ' + item['path'], flush=True)
            path.parent.mkdir(parents=True, exist_ok=True)
            # One monotonic deadline spans both attempts and their backoff.
            with download_deadline(file_timeout) as check_deadline:
                for attempt in range(2):
                    temp = None
                    try:
                        check_deadline()
                        with urllib.request.urlopen(base + item['path'], timeout=120) as response:
                            if response.status != 200:
                                raise ValueError('Unexpected download HTTP status')
                            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                                temp = Path(stream.name)
                                count = 0
                                while True:
                                    block = response.read(1024 * 1024)
                                    check_deadline()
                                    if not block:
                                        break
                                    count += len(block)
                                    if count > item['size']:
                                        raise ValueError('Model response exceeds locked size')
                                    stream.write(block)
                        with temp.open('rb') as stream:
                            beginning = stream.read(256).lstrip().lower()
                        if beginning.startswith((b'<!doctype html', b'<html', b'version https://git-lfs', b'{"error"')):
                            raise ValueError('Error page or Git LFS pointer instead of model')
                        if temp.stat().st_size != item['size'] or sha256(temp) != item['sha256']:
                            raise ValueError('Model size or SHA-256 mismatch: ' + item['path'])
                        temp.replace(path)
                        break
                    except urllib.error.HTTPError as error:
                        if error.code not in (502, 503, 504) or attempt == 1:
                            raise
                        time.sleep(1)
                    except (TimeoutError, urllib.error.URLError):
                        if attempt == 1:
                            raise
                        time.sleep(1)
                    finally:
                        if temp is not None and temp.exists():
                            temp.unlink()
        results.append({'path': str(path), 'sha256': item['sha256'], 'bytes': item['size']})
        print(('CACHED ' if valid else 'FETCHED ') + item['path'], flush=True)
    (cache / 'acquisition.json').write_text(json.dumps({
        'revision': manifest['revision'], 'license': manifest['license'],
        'files': results}, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    parser.add_argument('--lock', type=Path, default=root / 'model_sources/g2.lock.json')
    parser.add_argument('--cache', type=Path, default=root / '.artifacts/gazebo-model')
    parser.add_argument('--accept-noncommercial-license', action='store_true')
    parser.add_argument('--file-timeout', type=float, default=600,
                        help='Wall-clock seconds per file including retries (default: 600)')
    args = parser.parse_args()
    fetch(args.lock, args.cache, args.accept_noncommercial_license, args.file_timeout)


if __name__ == '__main__':
    main()
