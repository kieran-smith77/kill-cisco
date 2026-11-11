# Installation and removal

## Install from a checkout

Clone the repository using its hosting site's clone URL, or download and extract the ZIP. Keep the directory where you intend to use it; the installer points your shell at that checkout rather than copying files elsewhere.

From the repository directory:

```sh
./install.sh --dry-run
./install.sh
source ./cisco.aliases
cisco-status
```

Run the installer as your desktop user, without `sudo`. The runtime requests sudo when stopping Cisco. The installer makes no service, networking or certificate changes.

## Choose your startup file

The default follows your login shell in `$SHELL`:

| Shell | Default file |
| --- | --- |
| Zsh | `$ZDOTDIR/.zshrc` when ZDOTDIR is set; otherwise `~/.zshrc`. |
| Bash | `~/.bash_profile`, for the usual macOS login-shell setup. |

For interactive Bash shells that use `.bashrc`, or for another startup file:

```sh
./install.sh --rc-file "$HOME/.bashrc"
```

The selected file must be sourced by Bash or Zsh. Unsupported login shells require an explicit `--rc-file`; the functions themselves support Bash and Zsh.

You can install the source block in more than one startup file, but avoid sourcing it twice in the same shell startup chain. The installer quotes checkout paths, including spaces and shell characters. It replaces its own marked block when rerun and rejects malformed or duplicated markers. It preserves startup-file symlinks, existing file permissions and unrelated lines. A missing final newline is normalized when a file is rewritten.

Before a changed existing file is replaced, the installer creates a sibling backup named `<startup-file>.cisco-toggle-backup.<random>`. Keep backups until you have checked your shell startup. An unchanged installation produces no new backup.

## Updates and moving the checkout

Update using your normal Git workflow. Existing functions call the updated script, so a shell restart is normally unnecessary for runtime changes. Reload `cisco.aliases` or open a new terminal after changes to the functions themselves.

After moving the checkout, run `./install.sh` from its new location, using the same `--rc-file` if applicable. This updates the existing managed source block. Open a new terminal to load the new path.

## Without installation

From the checkout:

```sh
./cisco-client --help
./cisco-client --dry-run off
./cisco-client --dry-run on
./cisco-client status
```

Or load the shell functions for this terminal only:

```sh
source ./cisco.aliases
```

The runtime uses standard Cisco paths and rejects installations without the expected service helper. It does not discover or change legacy AnyConnect or Secure Client 5.0 services.

## Remove the shell integration

Restore Cisco first:

```sh
cisco-on
./install.sh --uninstall
```

For a custom startup file:

```sh
./install.sh --uninstall --rc-file "$HOME/.bashrc"
```

Repeat removal for each startup file where you installed the block. Open a new terminal to drop the functions, then delete the checkout if desired. The uninstaller removes only the managed source block and preserves the Cisco service state. It backs up changed files in the same way as installation.

If the checkout is already gone, remove the block between `# >>> Cisco Secure Client toggle >>>` and `# <<< Cisco Secure Client toggle <<<` from the affected startup file manually.
