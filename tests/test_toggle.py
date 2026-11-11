"""Lifecycle tests use command doubles; no installed Cisco service is changed."""
import os
from pathlib import Path
import shlex
import signal
import subprocess
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "cisco-client"

DOUBLES = r'''
source "$TEST_SCRIPT"
WAIT_SECONDS=1
preflight() { :; }
record() { printf '%s\n' "$*" >> "$TEST_LOG"; }
lc() {
    case "$*" in
        'print system')
            [[ ${DOMAIN_FAIL:-0} == 0 ]] ;;
        'print system/com.cisco.secureclient.vpn.service.agent')
            if [[ $(cat "$TEST_STATE") == on ]]; then
                printf 'state = running\n'
            elif [[ ${INSPECT_FAIL:-0} == 1 ]]; then
                printf 'Operation not permitted\n' >&2; return 1
            else
                printf 'Could not find service "com.cisco.secureclient.vpn.service.agent"\n' >&2
                return 113
            fi ;;
        *) record "unexpected launchctl: $*"; return 99 ;;
    esac
}
process_names() {
    [[ ${PS_FAIL:-0} == 0 ]] || return 1
    if [[ $(cat "$TEST_STATE") == on || ${CHILD_STUCK:-0} == 1 ]]; then
        printf '%s\n' vpnagentd /opt/cisco/secureclient/bin/acumbrellaagent \
            /opt/cisco/secureclient/bin/csc_swgagent /opt/cisco/secureclient/bin/dnscryptproxy
    fi
    printf '%s\n' /Applications/unrelated
}
admin_auth() { record auth; [[ ${AUTH_FAIL:-0} == 0 ]]; }
quit_service_app() { record quit; [[ ${QUIT_FAIL:-0} == 0 ]]; }
unregister_service() {
    record unregister
    if [[ ${STOP_FAIL:-0} == 1 ]]; then return 1; fi
    printf off > "$TEST_STATE"
}
open_service_app() {
    record open
    [[ ${START_FAIL:-0} == 0 ]] || return 1
    printf on > "$TEST_STATE"
}
open_client_app() {
    record open-ui
    [[ $(cat "$TEST_STATE") == on && ${UI_FAIL:-0} == 0 ]]
}
wait_tick() { :; }
main "$@"
'''


class ToggleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cisco lifecycle ")
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.state = self.base / "state"
        self.log = self.base / "log"
        self.state.write_text("on")
        self.log.write_text("")
        self.harness = self.base / "harness.sh"
        self.harness.write_text(DOUBLES)
        self.env = dict(os.environ, TEST_SCRIPT=str(SCRIPT), TEST_STATE=str(self.state),
                        TEST_LOG=str(self.log))

    def run_toggle(self, *args, **env):
        return subprocess.run(["/bin/bash", str(self.harness), *args],
                              env=dict(self.env, **env), text=True,
                              capture_output=True, timeout=10)

    def events(self):
        return self.log.read_text().splitlines()

    def test_stop_then_start_and_repetition(self):
        self.assertEqual(self.run_toggle("off").returncode, 0)
        self.assertEqual(self.state.read_text(), "off")
        self.assertEqual(self.events(), ["auth", "quit", "unregister"])
        self.assertEqual(self.run_toggle("off").returncode, 0)
        self.assertEqual(self.events(), ["auth", "quit", "unregister"])
        self.assertEqual(self.run_toggle("on").returncode, 0)
        self.assertEqual(self.state.read_text(), "on")
        self.assertEqual(self.run_toggle("on").returncode, 0)
        self.assertEqual(self.events().count("open"), 1)
        self.assertEqual(self.events().count("open-ui"), 2)
        self.assertEqual(self.events()[-3:], ["open", "open-ui", "open-ui"])

    def test_status_makes_no_changes(self):
        result = self.run_toggle("status")
        self.assertEqual(result.returncode, 0)
        self.assertIn("service: ON", result.stdout)
        self.assertIn("Umbrella=1  SWG=1", result.stdout)
        self.assertEqual(self.events(), [])

    def test_auth_cancellation_does_not_quit_or_unregister(self):
        result = self.run_toggle("off", AUTH_FAIL="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.events(), ["auth"])
        self.assertEqual(self.state.read_text(), "on")

    def test_stop_failure_does_not_run_command(self):
        result = self.run_toggle("run", "/bin/bash", "-c", 'printf BAD >> "$TEST_LOG"', STOP_FAIL="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("BAD", self.log.read_text())
        self.assertEqual(self.state.read_text(), "on")

    def test_quit_failure_does_not_unregister(self):
        self.assertNotEqual(self.run_toggle("off", QUIT_FAIL="1").returncode, 0)
        self.assertNotIn("unregister", self.events())

    def test_stuck_child_triggers_restore_and_failure(self):
        result = self.run_toggle("off", CHILD_STUCK="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("open", self.events())
        self.assertEqual(self.state.read_text(), "on")

    def test_command_failure_preserved_and_service_restored(self):
        result = self.run_toggle("run", "/bin/bash", "-c", "exit 37")
        self.assertEqual(result.returncode, 37)
        self.assertEqual(self.state.read_text(), "on")
        self.assertEqual(self.events(), ["auth", "quit", "unregister", "open", "open-ui"])

    def test_argv_working_directory_and_proxy_scope(self):
        output = self.base / "command output"
        command = 'printf "%s\\n" "$1" "$PWD" "${HTTPS_PROXY-unset}" > "$2"'
        result = self.run_toggle("run", "/bin/bash", "-c", command, "arg0",
                                 "spaces ; $(false) `false`", str(output),
                                 HTTPS_PROXY="http://proxy.invalid:3128")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output.read_text().splitlines(),
                         ["spaces ; $(false) `false`", os.getcwd(), "unset"])
        self.assertEqual(self.state.read_text(), "on")

    def test_already_off_runs_without_starting(self):
        self.state.write_text("off")
        result = self.run_toggle("run", "/usr/bin/true")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.events(), [])
        self.assertEqual(self.state.read_text(), "off")

    def test_restore_failure_is_failure_after_successful_command(self):
        for failure in ("START_FAIL", "UI_FAIL"):
            with self.subTest(failure=failure):
                self.state.write_text("on")
                result = self.run_toggle("run", "/usr/bin/true", **{failure: "1"})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("RESTORE FAILED", result.stderr)

    def test_inspection_failures_never_mean_off(self):
        for failure in ("DOMAIN_FAIL", "PS_FAIL", "INSPECT_FAIL"):
            with self.subTest(failure=failure):
                self.state.write_text("off")
                result = self.run_toggle("off", **{failure: "1"})
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.events(), [])

    def test_partial_state_rejected_by_wrapper(self):
        self.state.write_text("off")
        result = self.run_toggle("run", "/usr/bin/true", CHILD_STUCK="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("partial state", result.stderr)
        self.assertEqual(self.events(), [])

    def check_signal_restores_service(self, sig, expected):
        self.state.write_text("on")
        ready = self.base / "ready"
        ready.unlink(missing_ok=True)
        command = 'printf ready > "$1"; while :; do /bin/sleep 0.1; done'
        proc = subprocess.Popen(["/bin/bash", str(self.harness), "run", "/bin/bash", "-c",
                                 command, "arg0", str(ready)], env=self.env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, start_new_session=True)
        try:
            deadline = time.monotonic() + 5
            while not ready.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(ready.exists(), "wrapped command did not start")
            os.killpg(proc.pid, sig)
            _, stderr = proc.communicate(timeout=5)
            self.assertEqual(proc.returncode, expected, stderr)
            self.assertEqual(self.state.read_text(), "on")
            self.assertIn("open", self.events())
        finally:
            if proc.poll() is None:
                os.killpg(proc.pid, signal.SIGKILL)
                proc.communicate()

    def test_signals_restore_service(self):
        for sig, expected in ((signal.SIGTERM, 143), (signal.SIGINT, 130), (signal.SIGHUP, 129)):
            with self.subTest(signal=sig):
                self.check_signal_restores_service(sig, expected)

    def test_dry_run_does_not_mutate(self):
        for action in ("off", "on"):
            result = self.run_toggle("--dry-run", action)
            self.assertEqual(result.returncode, 0)
            self.assertIn("Would", result.stdout)
            if action == "on":
                self.assertIn("/Applications/Cisco/Cisco\\ Secure\\ Client.app", result.stdout)
        self.assertEqual(self.events(), [])

    def test_shell_functions_resolve_script_from_other_directory(self):
        for shell in ("/bin/bash", "/bin/zsh"):
            with self.subTest(shell=shell):
                command = f'source {shlex.quote(str(ROOT / "cisco.aliases"))}\nprintf "%s\\n" "$CISCO_TOGGLE_SCRIPT"\ncisco-status extra\n'
                result = subprocess.run([shell, "-c", command], cwd=self.base,
                                        capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(result.stdout.splitlines()[0], str(SCRIPT))
                self.assertIn("Usage:", result.stderr)

    def test_tls_issuer_check_and_inconclusive_results(self):
        for detail, curl_status, expected in (
            ("* issuer: O=Cisco; CN=Cisco Secure Access", 0, 2),
            ("* issuer: O=Amazon; CN=Amazon RSA 2048 M01", 0, 0),
            ("", 0, 1),
            ("* issuer: O=Amazon", 60, 1),
            ("timeout", 28, 1),
        ):
            with self.subTest(detail=detail, curl_status=curl_status):
                script = (f'source {shlex.quote(str(SCRIPT))}\n'
                          'curl_s3() { printf "%s\\n" "$TLS_DETAIL"; return "$CURL_STATUS"; }\n'
                          'check_tls\n')
                result = subprocess.run(["/bin/bash", "-c", script], capture_output=True,
                                        text=True, env=dict(self.env, TLS_DETAIL=detail,
                                                            CURL_STATUS=str(curl_status)), timeout=5)
                self.assertEqual(result.returncode, expected, result.stderr)


if __name__ == "__main__":
    unittest.main()
