# Troubleshooting and recovery

## Restore the service and open the main app

```sh
cisco-on
```

Without installed functions, run `./cisco-client on` from the checkout. It opens the service helper as the logged-in desktop user, waits for registration and the core VPN process, then opens Cisco Secure Client. The main app also opens when the core service is already running. Check the app for protected status and any required VPN login.

If the script cannot restore the service, open the helper and the main app manually from your desktop session:

```sh
open -a "/opt/cisco/secureclient/bin/Cisco Secure Client - AnyConnect VPN Service.app"
open -a "/Applications/Cisco/Cisco Secure Client.app"
```

Check macOS System Settings for background-item approvals if opening the helper does not start the service. Device management may control these approvals.

## Service shows PARTIAL or stop times out

The service registration and observed processes disagree, or a child process has not exited. Run `cisco-on` to recover. The script attempts restoration after an unsuccessful stop and returns a failure instead of reporting a completed pause.

Run one operation at a time. Concurrent wrappers can restore the service while another command still expects it paused. There is no shared lock or background watchdog.

## The S3 certificate still has a Cisco issuer

`cisco-check` returning `2` means that connection is still inspected. The core-service pause may not remove all interception: the socket filter, Zero Trust Access, a managed restart or a network proxy may still apply. Restore the client with `cisco-on`. An AWS destination or TLS-decryption exception in the applicable Secure Access policy may be needed.

The check bypasses explicit proxy environment variables and validates TLS normally. A non-Cisco issuer describes that connection only. It does not prove that an AWS API operation succeeds or that another region, service or application is uninspected.

## The TLS check fails or is inconclusive

Exit code `1` covers failed DNS, connections, TLS validation, timeouts and curl output without an issuer. The command reports the curl error code when available. Run a normal HTTPS connection check from Terminal and confirm that your network is available. Certificate validation stays enabled.

## Permission or desktop-session errors

Stopping requires sudo authorization. Opening apps requires a logged-in desktop user. When invoked as root, the script launches the apps in that desktop user's session rather than root's session. Run wrapped AWS or other commands as your normal user unless you intend them to run as root.

`status` also needs permission to inspect system launchd and the process list. Run it in a local Terminal if an application sandbox blocks those operations.

## The wrapper was killed or the Mac restarted

SIGKILL, a script crash or power loss cannot execute cleanup. Service unregistration may survive reboot. Run `cisco-on` afterward. The tool does not install a timer, daemon or watchdog to restore the service later.

## Installation issues

If commands are missing, open a new terminal or source `./cisco.aliases` from the checkout. Confirm that the installed source block is in a startup file your shell actually reads. Rerun installation after moving the checkout.

If the installer rejects malformed or duplicated markers, inspect the marked blocks and restore a backup or remove the duplicate block manually before retrying. It leaves the original file unchanged on that error.

For a bug report, include the macOS/client versions, command, exit code and relevant error text. Redact usernames, private hostnames, proxy URLs and organization details from diagnostic output. Do not attach enrollment files, credentials or full diagnostic bundles.
