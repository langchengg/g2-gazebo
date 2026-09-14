"""Project artifact fixtures; none is a vendor SDK or successful SDK smoke."""
import hashlib
import io
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import struct
import tarfile
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import zipfile

from agibot_g2_demo.sdk_acquisition import (
    AcquisitionError, fetch_installer, inspect_artifact, require_product_version,
)


class ProjectHTTPResponse(io.BytesIO):
    """Local response fixture; never a network socket or vendor response."""
    status = 200

    def __init__(self, body, length=None, on_first_read=None):
        super().__init__(body)
        self.headers = {} if length is None else {'Content-Length': length}
        self.on_first_read = on_first_read

    def read1(self, size):
        if self.on_first_read is not None:
            callback, self.on_first_read = self.on_first_read, None
            callback()
        return self.read(size)


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'project-fixture'

    def test_http_200_html_is_not_package(self):
        self.path.write_bytes(b'<!DOCTYPE html><title>Login</title>')
        with self.assertRaisesRegex(AcquisitionError, 'ERROR_DOCUMENT'):
            inspect_artifact(self.path)

    def test_json_error_is_not_package(self):
        self.path.write_bytes(b'{"error":"denied"}')
        with self.assertRaisesRegex(AcquisitionError, 'ERROR_DOCUMENT'):
            inspect_artifact(self.path)

    def test_empty_is_rejected(self):
        self.path.touch()
        with self.assertRaisesRegex(AcquisitionError, 'EMPTY'):
            inspect_artifact(self.path)

    def test_partial_is_rejected(self):
        partial = self.path.with_suffix('.part')
        partial.write_bytes(b'#!/bin/sh\nexit 0\n')
        with self.assertRaisesRegex(AcquisitionError, 'INCOMPLETE'):
            inspect_artifact(partial)

    def test_checksum_mismatch(self):
        self.path.write_bytes(b'#!/bin/sh\nexit 0\n')
        with self.assertRaisesRegex(AcquisitionError, 'CHECKSUM_MISMATCH'):
            inspect_artifact(self.path, '0' * 64)

    def test_script_not_sdk_or_product_version_proof(self):
        body = b'#!/bin/sh\n# A project fixture, never executed.\nexit 0\n'
        self.path.write_bytes(body)
        record = inspect_artifact(self.path, hashlib.sha256(body).hexdigest())
        self.assertFalse(record['sdk_downloaded'])
        self.assertFalse(record['executed'])
        self.assertEqual(record['product_version'], 'UNVERIFIED')
        self.assertEqual(record['bytes'], len(body))

    def test_malformed_zip_rejected(self):
        self.path.write_bytes(b'PK\x03\x04' + b'broken')
        with self.assertRaisesRegex(AcquisitionError, 'CORRUPT'):
            inspect_artifact(self.path)

    def test_zip_traversal_rejected(self):
        with zipfile.ZipFile(self.path, 'w') as archive:
            archive.writestr('../outside', 'project fixture')
        with self.assertRaisesRegex(AcquisitionError, 'UNSAFE'):
            inspect_artifact(self.path)

    def test_zip_absolute_rejected(self):
        with zipfile.ZipFile(self.path, 'w') as archive:
            archive.writestr('/outside', 'project fixture')
        with self.assertRaisesRegex(AcquisitionError, 'UNSAFE'):
            inspect_artifact(self.path)

    def test_zip_crc_corruption_rejected(self):
        with zipfile.ZipFile(self.path, 'w') as archive:
            archive.writestr('README', 'unique_project_fixture')
        self.path.write_bytes(self.path.read_bytes().replace(b'unique_project_fixture', b'broken_project_fixture'))
        with self.assertRaisesRegex(AcquisitionError, 'CORRUPT'):
            inspect_artifact(self.path)

    def test_truncated_tar_member_is_rejected(self):
        item = tarfile.TarInfo('payload')
        item.size = 5000
        self.path.write_bytes(item.tobuf() + b'incomplete')
        with self.assertRaisesRegex(AcquisitionError, 'CORRUPT'):
            inspect_artifact(self.path)

    def test_existing_partial_is_preserved_for_review(self):
        partial = self.path.parent / 'install.sh.part'
        partial.write_bytes(b'previous partial')
        with self.assertRaisesRegex(AcquisitionError, 'INCOMPLETE_CACHE'):
            fetch_installer('install.sh', self.path.parent)
        self.assertEqual(partial.read_bytes(), b'previous partial')

    def test_tar_symlink_rejected_without_extraction(self):
        with tarfile.open(self.path, 'w') as archive:
            item = tarfile.TarInfo('link')
            item.type = tarfile.SYMTYPE
            item.linkname = '/etc/passwd'
            archive.addfile(item)
        with self.assertRaisesRegex(AcquisitionError, 'UNSAFE'):
            inspect_artifact(self.path)
        self.assertFalse((self.path.parent / 'link').exists())

    def test_safe_archive_only_classified(self):
        with tarfile.open(self.path, 'w') as archive:
            item = tarfile.TarInfo('project-readme.txt')
            body = b'Project format fixture, NOT SDK'
            item.size = len(body)
            archive.addfile(item, io.BytesIO(body))
        record = inspect_artifact(self.path)
        self.assertEqual(record['format'], 'tar')
        self.assertEqual(record['entries'], ['project-readme.txt'])
        self.assertEqual(record['sdk_downloaded'], 'UNVERIFIED')
        self.assertEqual(record['product_version'], 'UNVERIFIED')
        self.assertFalse((self.path.parent / 'project-readme.txt').exists())

    def test_filename_does_not_validate_version(self):
        with self.assertRaisesRegex(AcquisitionError, 'VERSION_UNVERIFIED'):
            require_product_version(None)

    def test_wrong_internal_product_version(self):
        with self.assertRaisesRegex(AcquisitionError, 'VERSION_MISMATCH'):
            require_product_version('2.4.2')

    def test_unknown_download_resource_never_opens_network(self):
        with patch('urllib.request.build_opener', side_effect=AssertionError('network')):
            with self.assertRaisesRegex(AcquisitionError, 'UNVERIFIED_RESOURCE'):
                fetch_installer('guessed-package.whl', self.path.parent)

    def test_access_denied_is_reported_without_retry_or_credentials(self):
        for status in (401, 403, 429):
            opener = unittest.mock.Mock()
            opener.open.side_effect = urllib.error.HTTPError('private-url', status, 'denied', {}, None)
            with patch('urllib.request.build_opener', return_value=opener):
                with self.assertRaisesRegex(AcquisitionError, 'ACCESS_RESTRICTED_HTTP_' + str(status)):
                    fetch_installer('install.sh', self.path.parent)
            self.assertEqual(opener.open.call_count, 1)

    def test_mutated_cache_is_not_reused(self):
        installer = self.path.parent / 'install.sh'
        installer.write_bytes(b'#!/bin/sh\n# fixture\n')
        (self.path.parent / 'install.sh.sha256').write_text('0' * 64)
        with patch('urllib.request.build_opener', side_effect=AssertionError('network')):
            with self.assertRaisesRegex(AcquisitionError, 'CACHE_RECEIPT_MISMATCH'):
                fetch_installer('install.sh', self.path.parent)

    def test_checked_cache_is_reused_but_remains_unverified_sdk(self):
        installer = self.path.parent / 'install.sh'
        installer.write_bytes(b'#!/bin/sh\n# fixture\n')
        sha = hashlib.sha256(installer.read_bytes()).hexdigest()
        (self.path.parent / 'install.sh.sha256').write_text(sha)
        with patch('urllib.request.build_opener', side_effect=AssertionError('network')):
            record = fetch_installer('install.sh', self.path.parent)
        self.assertTrue(record['cache_reused'])
        self.assertFalse(record['sdk_downloaded'])

    def test_hashing_obeys_deadline_before_reading_rest_of_file(self):
        self.path.write_bytes(b'#!/bin/sh\n' + b'x' * 10000)
        clock = [0.0]
        real_hash = hashlib.sha256

        class ProjectTimedHash:
            def __init__(self):
                self.inner = real_hash()

            def update(self, block):
                self.inner.update(block)
                clock[0] = 31.0  # Deadline expires after the first hash chunk.

        with patch('agibot_g2_demo.sdk_acquisition.time.monotonic', side_effect=lambda: clock[0]), \
             patch('agibot_g2_demo.sdk_acquisition.hashlib.sha256', ProjectTimedHash):
            with self.assertRaisesRegex(AcquisitionError, 'inspection time bound'):
                inspect_artifact(self.path)

    def test_zip_member_read_obeys_deadline(self):
        with zipfile.ZipFile(self.path, 'w') as archive:
            archive.writestr('project-fixture', b'x' * 100)
        clock = [0.0]
        original_read = zipfile.ZipExtFile.read

        def delayed_read(member, size):
            data = original_read(member, size)
            clock[0] = 31.0
            return data

        with patch('agibot_g2_demo.sdk_acquisition.time.monotonic', side_effect=lambda: clock[0]), \
             patch.object(zipfile.ZipExtFile, 'read', delayed_read):
            with self.assertRaisesRegex(AcquisitionError, 'inspection time bound'):
                inspect_artifact(self.path)

    def test_zip_limits_and_names_checked_before_any_member_read(self):
        with zipfile.ZipFile(self.path, 'w') as archive:
            archive.writestr('first', '12345')
            archive.writestr('second', '12345')
        for setting, limit in (('MAX_ARCHIVE_ENTRIES', 1), ('MAX_ARCHIVE_BYTES', 4)):
            with self.subTest(setting=setting), \
                 patch('agibot_g2_demo.sdk_acquisition.' + setting, limit), \
                 patch.object(zipfile.ZipFile, 'open', side_effect=AssertionError('premature member read')):
                with self.assertRaisesRegex(AcquisitionError, 'ARCHIVE_REVIEW_REQUIRED'):
                    inspect_artifact(self.path)
        with zipfile.ZipFile(self.path, 'w') as archive:
            archive.writestr('first', 'safe')
            archive.writestr('../last', 'unsafe')
        with patch.object(zipfile.ZipFile, 'open', side_effect=AssertionError('premature member read')):
            with self.assertRaisesRegex(AcquisitionError, 'UNSAFE_ARCHIVE'):
                inspect_artifact(self.path)

    def test_corrupt_deflate_is_sanitized_acquisition_error(self):
        with zipfile.ZipFile(self.path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('private_project_fixture_token', b'x' * 100)
        body = bytearray(self.path.read_bytes())
        name_length, extra_length = struct.unpack_from('<HH', body, 26)
        body[30 + name_length + extra_length] = 7  # Invalid DEFLATE block type.
        self.path.write_bytes(body)
        with self.assertRaisesRegex(AcquisitionError, '^CORRUPT_ARCHIVE$') as caught:
            inspect_artifact(self.path)
        self.assertNotIn('private_project_fixture_token', str(caught.exception))
        self.assertTrue(caught.exception.__suppress_context__)

    def test_encrypted_and_unsupported_zip_are_review_errors(self):
        for kind in ('encrypted', 'unsupported'):
            with self.subTest(kind=kind):
                with zipfile.ZipFile(self.path, 'w') as archive:
                    archive.writestr('private_project_fixture_token', b'fixture')
                body = bytearray(self.path.read_bytes())
                central = body.index(b'PK\x01\x02')
                if kind == 'encrypted':
                    struct.pack_into('<H', body, 6, 1)
                    struct.pack_into('<H', body, central + 8, 1)
                else:
                    struct.pack_into('<H', body, 8, 99)
                    struct.pack_into('<H', body, central + 10, 99)
                self.path.write_bytes(body)
                with self.assertRaisesRegex(AcquisitionError, 'ARCHIVE_REVIEW_REQUIRED') as caught:
                    inspect_artifact(self.path)
                self.assertNotIn('private_project_fixture_token', str(caught.exception))
                self.assertTrue(caught.exception.__suppress_context__)

    def fetch_with_response(self, response):
        opener = unittest.mock.Mock()
        opener.open.return_value = response
        with patch('urllib.request.build_opener', return_value=opener):
            return fetch_installer('install.sh', self.path.parent)

    def test_invalid_content_length_is_sanitized_before_publication(self):
        for length in ('signed-url?token=private', '-1', '1.5', '', '9' * 100):
            with self.subTest(length=length):
                response = ProjectHTTPResponse(b'#!/bin/sh\n', length)
                with self.assertRaisesRegex(AcquisitionError, '^INVALID_CONTENT_LENGTH$'):
                    self.fetch_with_response(response)
                self.assertEqual(list(self.path.parent.iterdir()), [])

    def test_truncated_transfer_removes_only_own_unique_temp(self):
        with self.assertRaisesRegex(AcquisitionError, 'Content-Length mismatch'):
            self.fetch_with_response(ProjectHTTPResponse(b'#!/bin/sh\n', '100'))
        self.assertEqual(list(self.path.parent.iterdir()), [])

    def test_concurrent_destination_is_not_overwritten_and_receipt_is_checked(self):
        winner = b'#!/bin/sh\n# other project fixture won publication\n'
        loser = b'#!/bin/sh\n# this project fixture lost publication\n'
        destination = self.path.parent / 'install.sh'
        receipt = self.path.parent / 'install.sh.sha256'

        def publish_other():
            destination.write_bytes(winner)
            receipt.write_text(hashlib.sha256(winner).hexdigest())

        record = self.fetch_with_response(ProjectHTTPResponse(loser, on_first_read=publish_other))
        self.assertTrue(record['cache_reused'])
        self.assertEqual(destination.read_bytes(), winner)
        self.assertEqual(record['sha256'], hashlib.sha256(winner).hexdigest())
        self.assertEqual(list(self.path.parent.glob('.*.part')), [])

    def test_concurrent_bad_receipt_is_preserved_and_rejected(self):
        destination = self.path.parent / 'install.sh'
        receipt = self.path.parent / 'install.sh.sha256'

        def publish_other():
            destination.write_bytes(b'#!/bin/sh\n# other fixture\n')
            receipt.write_text('0' * 64)

        with self.assertRaisesRegex(AcquisitionError, 'CACHE_RECEIPT_MISMATCH'):
            self.fetch_with_response(ProjectHTTPResponse(b'#!/bin/sh\n', on_first_read=publish_other))
        self.assertEqual(destination.read_bytes(), b'#!/bin/sh\n# other fixture\n')
        self.assertEqual(receipt.read_text(), '0' * 64)
        self.assertEqual(list(self.path.parent.glob('.*.part')), [])

    def test_failure_does_not_delete_another_calls_legacy_partial(self):
        other = self.path.parent / 'install.sh.part'

        def fail_after_other_started():
            other.write_bytes(b'other project fixture partial')
            raise TimeoutError('https://private.invalid/?token=not-real')

        with self.assertRaisesRegex(AcquisitionError, '^TRANSPORT_FAILURE: TimeoutError$'):
            self.fetch_with_response(ProjectHTTPResponse(b'', on_first_read=fail_after_other_started))
        self.assertEqual(other.read_bytes(), b'other project fixture partial')
        self.assertEqual(list(self.path.parent.glob('.*.part')), [])

    def test_cleanup_preserves_replaced_temporary_inode(self):
        replacement = []

        def replace_then_fail():
            temporary = next(self.path.parent.glob('.install.sh.*.part'))
            temporary.unlink()
            temporary.write_bytes(b'other owner replacement')
            replacement.append(temporary)
            raise TimeoutError('project fixture')

        with self.assertRaisesRegex(AcquisitionError, 'TRANSPORT_FAILURE'):
            self.fetch_with_response(ProjectHTTPResponse(b'', on_first_read=replace_then_fail))
        self.assertEqual(replacement[0].read_bytes(), b'other owner replacement')

    def test_two_simultaneous_fetches_have_unique_temporaries(self):
        barrier = threading.Barrier(2)
        first_done = threading.Event()
        local = threading.local()
        body = b'#!/bin/sh\n# project concurrency fixture\n'

        def run(index):
            def during_read():
                barrier.wait(timeout=2)
                if index == 1:
                    if not first_done.wait(timeout=2):
                        raise AssertionError('first publication did not complete')
            local.opener = unittest.mock.Mock()
            local.opener.open.return_value = ProjectHTTPResponse(body, str(len(body)), during_read)
            try:
                return fetch_installer('install.sh', self.path.parent)
            finally:
                if index == 0:
                    first_done.set()

        with patch('urllib.request.build_opener', side_effect=lambda *args: local.opener):
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(run, index) for index in (0, 1)]
                records = [future.result(timeout=4) for future in futures]
        self.assertFalse(records[0]['cache_reused'])
        self.assertTrue(records[1]['cache_reused'])
        self.assertEqual((self.path.parent / 'install.sh').read_bytes(), body)
        self.assertEqual(list(self.path.parent.glob('.*.part')), [])
