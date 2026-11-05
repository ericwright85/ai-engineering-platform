import os
import unittest

class SandboxContract(unittest.TestCase):
    def test_nonroot_and_no_host_secret(self):
        self.assertNotEqual(0, os.getuid())
        self.assertNotIn('GITHUB_TOKEN', os.environ)
        self.assertFalse(os.path.exists('/var/run/docker.sock'))

    def test_source_is_read_only(self):
        with self.assertRaises(OSError):
            with open('/repo/should-not-exist', 'w') as output:
                output.write('no')
