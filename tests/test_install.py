"""Exercise shell integration against temporary files, never real startup files."""
import os
from pathlib import Path
import shlex
import shutil
import stat
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BEGIN = "# >>> Cisco Secure Client toggle >>>"
END = "# <<< Cisco Secure Client toggle <<<"


@unittest.skipIf(os.geteuid() == 0, "The installer intentionally rejects root")
class InstallTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cisco install ")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.repo = self.base / "checkout spaces ' $(touch SHOULD_NOT_EXIST)"
        self.repo.mkdir()
        for name in ("install.sh", "cisco.aliases", "cisco-client"):
            shutil.copy2(ROOT / name, self.repo / name)
        self.rc = self.base / "shell startup"

    def install(self, *args, rc=None):
        return subprocess.run(["/bin/bash", str(self.repo / "install.sh"),
                               "--rc-file", str(rc or self.rc), *args],
                              cwd=self.base, text=True, capture_output=True, timeout=5)

    def backups(self, path=None):
        path = path or self.rc
        return list(path.parent.glob(path.name + ".cisco-toggle-backup.*"))

    def test_fresh_install_quotes_paths_for_bash_and_zsh(self):
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.rc.read_text().count(BEGIN), 1)
        self.assertEqual(self.backups(), [])
        command = ('source ' + shlex.quote(str(self.rc)) + '\n'
                   'printf "%s\\n" "$CISCO_TOGGLE_SCRIPT"\n')
        for shell in ("/bin/bash", "/bin/zsh"):
            with self.subTest(shell=shell):
                sourced = subprocess.run([shell, "-f", "-c", command], cwd=self.base,
                                         text=True, capture_output=True, timeout=5)
                self.assertEqual(sourced.returncode, 0, sourced.stderr)
                self.assertEqual(sourced.stdout.strip(), str(self.repo / "cisco-client"))
        self.assertFalse((self.base / "SHOULD_NOT_EXIST").exists())

    def test_install_uninstall_preserves_content_mode_and_backups(self):
        original = "# User configuration\nexport CISCO_TEST_SETTING='keep me'\n"
        self.rc.write_text(original)
        self.rc.chmod(0o640)
        self.assertEqual(self.install().returncode, 0)
        self.assertTrue(self.rc.read_text().startswith(original))
        self.assertEqual(stat.S_IMODE(self.rc.stat().st_mode), 0o640)
        self.assertEqual(len(self.backups()), 1)
        self.assertEqual(self.backups()[0].read_text(), original)
        installed = self.rc.read_text()
        self.assertEqual(self.install().returncode, 0)
        self.assertEqual(self.rc.read_text(), installed)
        self.assertEqual(len(self.backups()), 1)
        self.assertEqual(self.install("--uninstall").returncode, 0)
        self.assertEqual(self.rc.read_text(), original)
        self.assertEqual(len(self.backups()), 2)
        self.assertEqual(self.install("--uninstall").returncode, 0)
        self.assertEqual(len(self.backups()), 2)

    def test_relative_file_symlink_is_preserved(self):
        target = self.base / "actual startup"
        target.write_text("# Original\n")
        self.rc.symlink_to(target.name)
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.rc.is_symlink())
        self.assertIn(BEGIN, target.read_text())
        self.assertEqual(len(self.backups(target)), 1)
        self.assertEqual(self.install("--uninstall").returncode, 0)
        self.assertTrue(self.rc.is_symlink())
        self.assertEqual(target.read_text(), "# Original\n")

    def test_malformed_markers_do_not_change_file(self):
        cases = (BEGIN + "\nunfinished\n", END + "\n",
                 f"{BEGIN}\n{END}\n{BEGIN}\n{END}\n")
        for content in cases:
            with self.subTest(content=content):
                self.rc.write_text(content)
                result = self.install()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("malformed or duplicated", result.stderr)
                self.assertEqual(self.rc.read_text(), content)
                self.assertEqual(self.backups(), [])

    def test_dry_run_does_not_create_startup_directory(self):
        absent = self.base / "missing" / ".zshrc"
        for args in (("--dry-run",), ("--dry-run", "--uninstall")):
            with self.subTest(args=args):
                result = self.install(*args, rc=absent)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse(absent.parent.exists())

    def test_uninstall_absent_or_unmanaged_file_is_no_op(self):
        self.assertEqual(self.install("--uninstall").returncode, 0)
        self.assertFalse(self.rc.exists())
        original = "# Existing file without final newline"
        self.rc.write_text(original)
        self.assertEqual(self.install("--uninstall").returncode, 0)
        self.assertEqual(self.rc.read_text(), original)
        self.assertEqual(self.backups(), [])

    def test_reinstall_after_move_replaces_old_source_block(self):
        self.assertEqual(self.install().returncode, 0)
        moved = self.base / "moved checkout"
        self.repo.rename(moved)
        self.repo = moved
        result = self.install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.rc.read_text().count(BEGIN), 1)
        self.assertNotIn("SHOULD_NOT_EXIST", self.rc.read_text())
        self.assertIn("moved\\ checkout/cisco.aliases", self.rc.read_text())

    def test_rejects_unknown_arguments_and_directories(self):
        self.assertNotEqual(self.install("--typo").returncode, 0)
        self.assertFalse(self.rc.exists())
        self.rc.mkdir()
        self.assertNotEqual(self.install().returncode, 0)

    def test_file_symlink_loop_fails_without_modification(self):
        self.rc.symlink_to(self.rc.name)
        result = self.install()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink loop", result.stderr)
        self.assertTrue(self.rc.is_symlink())


if __name__ == "__main__":
    unittest.main()
