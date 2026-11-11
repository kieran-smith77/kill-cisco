# Development and validation

## Local checks

On macOS with Python 3.8+:

```sh
/bin/bash -n cisco-client
/bin/bash -n install.sh
/bin/bash -n cisco.aliases
/bin/zsh -n cisco.aliases
python3 -m unittest discover -s tests -v
```

The runtime and installer use macOS's built-in Bash 3.2 and command-line tools. Tests use Python's standard library. No Python package installation is required.

The GitHub Actions workflow runs syntax checks and the same test suite on `macos-15` and `macos-26`. It uses simulated service commands and temporary startup files, so it does not need Cisco, AWS credentials or sudo. A configured workflow is not evidence of a completed hosted run; inspect the repository's Actions results after pushing it.

## What the tests cover

- Repeated stop/start and opening the main app after restoration, including an already-running service.
- Authentication cancellation, failed service operations, partial process state and restoration errors.
- Wrapped command arguments, working directory, proxy scope and command exit status.
- Restoration after INT, HUP and TERM; preserving an already-stopped service.
- TLS issuer classification, network failure and inconclusive output through command doubles.
- Installation/removal, backups, symlinks, repeated installation and quoted checkout paths.

These checks validate local control flow and file handling. They do not exercise real service unregistration, enrollment, native authorization dialogs, managed policy, protected-state reconnection or signed AWS requests. End-to-end operation on an enrolled client remains unverified.

## Optional manual client validation

On an authorized test Mac with a working desktop session, first record `./cisco-client status` and `./cisco-client check`. Run `./cisco-client off`, check the resulting state and certificate issuer, then restore with `./cisco-client on`. Confirm the main app opens and reports the expected protection state. Keep the manual restore commands in [troubleshooting](troubleshooting.md) available throughout testing.

Record the OS and client versions and distinguish service state, TLS observation and actual application behavior. Avoid committing raw diagnostic logs or enrollment data. A successful service pause alone does not establish a traffic bypass.

## Publishing a new repository

This directory is self-contained; its Git history should contain only this utility. Create an empty repository in the intended hosting account, add its clone URL as `origin`, and push `main` using your normal Git workflow. Review the initial commit's author metadata and [MIT license](../LICENSE) before publishing.

No hosting account or remote URL is embedded in the scripts or installation process. The shell functions continue to use this local checkout independently of where the repository is hosted.
