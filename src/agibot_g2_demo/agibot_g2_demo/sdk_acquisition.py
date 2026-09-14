"""Inspect acquisition artifacts without executing installers or vendor code.

The only fetchable resources are the two installer URLs actually published in
GDK 2.6.3 deployment instructions. An installer is NOT the SDK product payload.
No robots are scanned, no controller APIs are called, and nothing is installed.
"""
from __future__ import annotations

import hashlib
import http.client
import lzma
import os
from pathlib import Path, PurePosixPath
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
import zlib

SOURCE_PAGE = 'https://support.agibot.com/?gdk_version=2.6.3#contents/howto/deploy.md'
RESOURCES = {name: 'http://10.42.1.101:8849/' + name
             for name in ('install.sh', 'install_example.sh')}
MAX_INSTALLER_BYTES = 16 * 1024 * 1024  # Project resource bound, not a vendor limit.
MAX_ARCHIVE_BYTES = 2 * 1024**3
MAX_ARCHIVE_ENTRIES = 20000


class AcquisitionError(ValueError):
    """Artifact or transfer is not acceptable evidence."""


def require_product_version(observed: str | None) -> None:
    if observed is None:
        raise AcquisitionError('VERSION_UNVERIFIED: no internal product version evidence')
    if observed != '2.6.3':
        raise AcquisitionError('VERSION_MISMATCH: required product GDK 2.6.3')


def _check_deadline(deadline: float) -> None:
    if time.monotonic() > deadline:
        raise AcquisitionError('ARTIFACT_REVIEW_REQUIRED: inspection time bound')


def _check_name(name: str, seen: set[str]) -> None:
    parts = PurePosixPath(name)
    if parts.is_absolute() or '..' in parts.parts or '\\' in name or ':' in name:
        raise AcquisitionError('UNSAFE_ARCHIVE: absolute or traversal path')
    if name in seen:
        raise AcquisitionError('UNSAFE_ARCHIVE: duplicate entry')
    seen.add(name)
    if len(seen) > MAX_ARCHIVE_ENTRIES:
        raise AcquisitionError('ARCHIVE_REVIEW_REQUIRED: too many entries')


def _read_member(member, expected_size: int, deadline: float) -> None:
    """Read through EOF so ZipExtFile validates CRC, without an unbounded testzip."""
    count = 0
    while True:
        _check_deadline(deadline)
        block = member.read(1024 * 1024)
        _check_deadline(deadline)
        if not block:
            break
        count += len(block)
        if count > expected_size:
            raise AcquisitionError('CORRUPT_ARCHIVE: member size mismatch')
    if count != expected_size:
        raise AcquisitionError('CORRUPT_ARCHIVE: truncated member')


def inspect_artifact(path: Path, expected_sha256: str | None = None) -> dict:
    """Static format/hash inspection, NEVER proof of official provenance/version.

    Archive contents are listed and validated, never extracted. Reject all
    links/special entries; there is no need to resolve dangerous SDK symlinks
    before the actual distribution layout and its purpose have been reviewed.
    """
    if path.suffix in ('.part', '.partial'):
        raise AcquisitionError('INCOMPLETE: temporary download suffix')
    if not path.is_file() or path.is_symlink():
        raise AcquisitionError('MISSING_ARTIFACT: expected a regular local file')
    deadline = time.monotonic() + 30
    digest = hashlib.sha256()
    try:
        with path.open('rb') as stream:
            _check_deadline(deadline)
            head = stream.read(4096)
            _check_deadline(deadline)
            digest.update(head)
            while True:
                _check_deadline(deadline)
                block = stream.read(1024 * 1024)
                _check_deadline(deadline)
                if not block:
                    break
                digest.update(block)
    except OSError:
        raise AcquisitionError('ARTIFACT_READ_FAILURE') from None
    if not head:
        raise AcquisitionError('EMPTY_ARTIFACT')
    lower = head.lstrip().lower()
    if lower.startswith((b'<', b'{', b'[')):
        raise AcquisitionError('ERROR_DOCUMENT: HTML/XML/JSON is not an SDK artifact')
    sha = digest.hexdigest()
    if expected_sha256 is not None and sha != expected_sha256:
        raise AcquisitionError('CHECKSUM_MISMATCH')
    kind = None
    entries = []
    total_bytes = 0
    seen = set()
    try:
        _check_deadline(deadline)
        if zipfile.is_zipfile(path):
            kind = 'wheel' if path.suffix == '.whl' else 'zip'
            with zipfile.ZipFile(path) as archive:
                _check_deadline(deadline)
                if len(archive.infolist()) > MAX_ARCHIVE_ENTRIES:
                    raise AcquisitionError('ARCHIVE_REVIEW_REQUIRED: too many entries')
                # Validate every name/count/size before reading any member data.
                for entry in archive.infolist():
                    _check_deadline(deadline)
                    mode = entry.external_attr >> 16
                    if mode & 0o170000 == 0o120000:
                        raise AcquisitionError('UNSAFE_ARCHIVE: symlink')
                    _check_name(entry.filename, seen)
                    entries.append(entry.filename)
                    total_bytes += entry.file_size
                    if total_bytes > MAX_ARCHIVE_BYTES:
                        raise AcquisitionError('ARCHIVE_REVIEW_REQUIRED: expanded size bound')
                for entry in archive.infolist():
                    _check_deadline(deadline)
                    with archive.open(entry) as member:
                        _read_member(member, entry.file_size, deadline)
        elif tarfile.is_tarfile(path):
            kind = 'tar'
            with tarfile.open(path) as archive:
                for entry in archive:
                    _check_deadline(deadline)
                    if not (entry.isfile() or entry.isdir()):
                        raise AcquisitionError('UNSAFE_ARCHIVE: link or special entry')
                    _check_name(entry.name, seen)
                    entries.append(entry.name)
                    total_bytes += entry.size
                    if total_bytes > MAX_ARCHIVE_BYTES:
                        raise AcquisitionError('ARCHIVE_REVIEW_REQUIRED: expanded size bound')
                    if entry.isfile():
                        with archive.extractfile(entry) as member:
                            _read_member(member, entry.size, deadline)
        elif head.startswith(b'#!') and b'\x00' not in head:
            kind = 'installer-script'
        elif head.startswith(b'\x7fELF'):
            kind = 'ELF'
        elif head.startswith(b'!<arch>\n') and path.suffix == '.deb':
            kind = 'deb'  # dpkg-deb inspection remains necessary on Linux.
        else:
            raise AcquisitionError('UNKNOWN_OR_CORRUPT_FORMAT')
    except (tarfile.TarError, zipfile.BadZipFile, EOFError, OSError, zlib.error, lzma.LZMAError):
        raise AcquisitionError('CORRUPT_ARCHIVE') from None
    except RuntimeError:
        # Includes encrypted ZIP/no password and unsupported compression methods.
        # Do not expose exception text containing archive names or other input.
        raise AcquisitionError('ARCHIVE_REVIEW_REQUIRED: encrypted or unsupported compression') from None
    _check_deadline(deadline)
    return {'path': str(path.resolve()), 'bytes': path.stat().st_size, 'sha256': sha,
            'format': kind, 'entries': entries, 'product_version': 'UNVERIFIED',
            'official_integrity': 'NOT PROVIDED' if expected_sha256 is None else
            'MATCHED_SUPPLIED_HASH; independent official provenance still required',
            'sdk_downloaded': False if kind == 'installer-script' else 'UNVERIFIED',
            'executed': False}


class _ReviewRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Do not log a potentially signed Location header. Review it privately.
        raise AcquisitionError('REDIRECT_REVIEW_REQUIRED: installer resource moved')


def _checked_installer_cache(destination: Path) -> dict:
    record = inspect_artifact(destination)
    if record['format'] != 'installer-script':
        raise AcquisitionError('INVALID_INSTALLER_CACHE')
    receipt = destination.with_name(destination.name + '.sha256')
    try:
        if (not receipt.is_file() or receipt.is_symlink() or receipt.stat().st_size > 128
                or receipt.read_text(encoding='ascii').strip() != record['sha256']):
            raise AcquisitionError('CACHE_RECEIPT_MISMATCH')
    except (OSError, UnicodeError):
        raise AcquisitionError('CACHE_RECEIPT_MISMATCH') from None
    return dict(record, cache_reused=True, source_page=SOURCE_PAGE)


def fetch_installer(name: str, directory: Path) -> dict:
    if name not in RESOURCES:
        raise AcquisitionError('UNVERIFIED_RESOURCE: not in official deployment page')
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / name
    if destination.exists():
        return _checked_installer_cache(destination)
    # The documented IP is robot-local. Do not route it through an unrelated
    # ambient HTTP proxy or disclose any proxy credentials in evidence output.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _ReviewRedirect())
    if (directory / (name + '.part')).exists():
        raise AcquisitionError('INCOMPLETE_CACHE_REVIEW_REQUIRED: existing partial file preserved')
    receipt = directory / (name + '.sha256')
    if receipt.exists():
        raise AcquisitionError('CACHE_RECEIPT_WITHOUT_ARTIFACT: review existing receipt')
    deadline = time.monotonic() + 12
    part = None
    part_identity = None
    try:
        with opener.open(RESOURCES[name], timeout=4) as response:
            if response.status != 200:
                raise AcquisitionError('HTTP_STATUS_' + str(response.status))
            length = response.headers.get('Content-Length')
            expected_length = None
            if length is not None:
                # Header contents are untrusted and must never enter an error.
                normalized = length.strip()
                if (not normalized or len(normalized) > 20 or not normalized.isascii()
                        or not normalized.isdecimal()):
                    raise AcquisitionError('INVALID_CONTENT_LENGTH')
                expected_length = int(normalized)
                if expected_length > MAX_INSTALLER_BYTES:
                    raise AcquisitionError('INSTALLER_SIZE_EXCEEDED')
            fd, temporary_name = tempfile.mkstemp(prefix='.' + name + '.', suffix='.part', dir=directory)
            part = Path(temporary_name)
            stat = os.fstat(fd)
            part_identity = (stat.st_dev, stat.st_ino)
            size = 0
            with os.fdopen(fd, 'wb') as stream:
                while True:
                    if time.monotonic() > deadline:
                        raise AcquisitionError('TRANSFER_TIMEOUT')
                    block = response.read1(65536)
                    if time.monotonic() > deadline:
                        raise AcquisitionError('TRANSFER_TIMEOUT')
                    if not block:
                        break
                    size += len(block)
                    if size > MAX_INSTALLER_BYTES:
                        raise AcquisitionError('INSTALLER_SIZE_EXCEEDED')
                    stream.write(block)
            if expected_length is not None and size != expected_length:
                raise AcquisitionError('INCOMPLETE: Content-Length mismatch')
        # Inspect without renaming a .part into a valid package prematurely.
        body = part.read_bytes()
        if not body.startswith(b'#!') or b'\x00' in body:
            raise AcquisitionError('INVALID_INSTALLER: expected script, not HTML/error/package')
        try:
            # Hard-link publication is atomic and fails if another call won.
            # Unlike rename(), it never overwrites a concurrent destination.
            os.link(part, destination)
        except FileExistsError:
            return _checked_installer_cache(destination)
        result = inspect_artifact(destination)
        if result['sha256'] != hashlib.sha256(body).hexdigest():
            raise AcquisitionError('CACHE_CHANGED_DURING_PUBLICATION')
        # Exclusive receipt creation also preserves a concurrent/user receipt.
        with receipt.open('x', encoding='ascii') as stream:
            stream.write(result['sha256'] + '\n')
        return dict(result, cache_reused=False, source_page=SOURCE_PAGE)
    except urllib.error.HTTPError as error:
        status = error.code
        error.close()
        raise AcquisitionError('ACCESS_RESTRICTED_HTTP_' + str(status) if status in
                               (401, 403, 429) else 'HTTP_STATUS_' + str(status)) from None
    except (urllib.error.URLError, TimeoutError, OSError, http.client.HTTPException) as error:
        # Exception messages can include URLs/secrets; record only safe class.
        raise AcquisitionError('TRANSPORT_FAILURE: ' + type(error).__name__) from None
    finally:
        if part is not None:
            try:
                stat = part.lstat()
                if (stat.st_dev, stat.st_ino) == part_identity:
                    part.unlink()  # Only the unique inode this call created.
            except FileNotFoundError:
                pass
