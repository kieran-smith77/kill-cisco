# Contributing

Please describe the concrete failure, expected behavior, macOS/client versions and the validation performed. Keep diagnostic output free of enrollment data, credentials and organization-specific details.

Use macOS's built-in Bash 3.2 syntax for scripts and preserve Bash/Zsh function compatibility. Keep service control scoped to the documented Core/Umbrella helper lifecycle. Changes to networking, installed client files or managed policy need a separate design discussion.

Run the checks in [development and validation](docs/development.md). Keep automated tests independent of installed Cisco services and user startup files; installation tests must use temporary files. Document the evidence boundary for any manual client testing.
