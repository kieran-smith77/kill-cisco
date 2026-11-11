# Secure Client Toggle

Pause and restore Cisco Secure Client's Core/Umbrella service on macOS from your terminal. Includes shell functions, a command wrapper with automatic restoration, and a public S3 TLS inspection check.

Designed for **macOS 13+ and Secure Client 5.1 with the bundled AnyConnect VPN Service helper**. Use where you are authorized to manage the client. The pause affects the whole Mac and disconnects active AnyConnect VPN sessions. Service unregistration can survive reboot: restore with `cisco-on` when finished.

## Install

Clone this repository, or download and extract its ZIP, to a directory you will keep. From that directory:

```sh
./install.sh --dry-run
./install.sh
```

Open a new terminal, then:

```sh
cisco-status
cisco-off       # asks for sudo
cisco-check     # inspect the certificate issuer on a public S3 endpoint
# Run your command here.
cisco-on        # restore the service and open the main Cisco Secure Client app
```

The installer uses your `$SHELL`: Zsh gets `${ZDOTDIR:-$HOME}/.zshrc`; Bash gets `~/.bash_profile`. Select a different file with `./install.sh --rc-file "$HOME/.bashrc"`. It adds one managed source block, preserves startup-file symlinks, and backs up changed files alongside their targets. Repeating installation is safe. Installation does not require sudo or change Cisco's state.

Keep the checkout in place: the shell functions run its script. To use the functions immediately, run `source ./cisco.aliases`. You can also skip installation and run `./cisco-client status` directly. See [installation and removal](docs/installation.md) for details.

## Commands

| Shell function | Script command | Behavior |
| --- | --- | --- |
| `cisco-off` / `kill-cisco` | `./cisco-client off` | Pause Core VPN, Umbrella and its SWG/DNS child processes. |
| `cisco-on` / `start-cisco` | `./cisco-client on` | Restore the service, then open Cisco Secure Client as the desktop user. |
| `cisco-toggle` | `./cisco-client toggle` | Switch between running and stopped states. |
| `cisco-status` | `./cisco-client status` | Show service registration and process state. |
| `cisco-check` | `./cisco-client check` | Check the TLS issuer at `s3.eu-west-1.amazonaws.com`. |
| `without-cisco COMMAND ...` | `./cisco-client run COMMAND ...` | Pause for a command, then attempt restoration. |

For one command:

```sh
without-cisco aws s3api list-buckets --profile YOUR_PROFILE
```

For a five-minute pause with restoration on completion or Ctrl-C:

```sh
without-cisco sleep 300
```

The wrapper runs the command as the invoking user and preserves its arguments, working directory and AWS configuration. HTTP/HTTPS/ALL proxy environment variables are cleared for that command. It attempts restoration on completion, command failure, Ctrl-C, HUP and TERM. If Cisco was already off, it leaves it off. SIGKILL, script crashes and power loss cannot run cleanup; use `cisco-on` afterward. Run one toggle or wrapper operation at a time.

## How it works

The script follows [Cisco's documented stop/start procedure for macOS 13+ and Secure Client 5.1](https://www.cisco.com/c/en/us/support/docs/security/umbrella/224731-disable-or-restart-the-umbrella-roaming.html). It quits the AnyConnect VPN Service helper, uses that helper's `uninstall` argument to unregister the background service, and restores it by opening the helper again. The service helper's argument does not remove the Cisco product or its enrollment.

After restoration, the script also opens `/Applications/Cisco/Cisco Secure Client.app`, including when the service was already running. Core registration and the VPN agent are checked before opening the main app; Umbrella/SWG reconnection and any VPN login may still take time or require interaction.

Stopping waits for the core registration, `vpnagentd`, Umbrella, SWG and Cisco DNS proxy to disappear. A failed stop attempts restoration. The script leaves network-extension registrations and Zero Trust Access separately managed. It does not alter routing tables, DNS configuration or TLS trust.

## Verify the result

Stopping a service is **not proof that traffic bypasses inspection**. A socket filter, another Cisco component, device management or a network proxy may still intercept traffic or restart the service. `cisco-check` makes a public, credential-free HEAD request to S3 with certificate validation enabled, explicit proxies bypassed and a 12-second timeout.

| Check exit code | Meaning |
| --- | --- |
| `0` | No Cisco/Umbrella issuer observed for this connection. Other traffic and signed AWS operations are unverified. |
| `1` | Request failed or issuer could not be determined. |
| `2` | Cisco/Umbrella TLS interception was detected. |

If interception remains, run `cisco-on` and use a destination or decryption exception in your organization's policy. See [troubleshooting and recovery](docs/troubleshooting.md).

## Requirements and verification

- macOS with `/bin/bash` and the Secure Client 5.1 helper at its standard path.
- An administrator account for stopping the service and a logged-in desktop session for opening the apps.
- Bash or Zsh for the shell functions. Python 3.8+ is needed only to run the tests.

Automated tests simulate service commands, process state and installation into temporary startup files. GitHub Actions is configured for macOS 15 and 26. These tests do not install Cisco, prove an enrolled client's reconnect behavior or certify bypass of inspection. End-to-end stop/start and signed AWS operations remain unverified. See [development and validation](docs/development.md).

## Uninstall

Restore Cisco with `cisco-on`, then remove the shell integration:

```sh
./install.sh --uninstall
```

Use the same `--rc-file` if you selected a custom one. Open a new terminal; you can then delete the checkout. Uninstallation removes this tool's shell integration and does not change the Cisco service state.

## License and acknowledgments

[MIT](LICENSE). Inspired by the shell-toggle experience of [bkahlert/kill-zscaler](https://github.com/bkahlert/kill-zscaler). This is an independent utility and is not affiliated with Cisco.
