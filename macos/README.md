# Mac app

The standalone universal app uses the existing journal services and dashboard,
an AppKit/WebKit window, and bundled Python 3.12.14 runtimes. It requires macOS 12+.
Users install from the DMG without Python, Node, Terminal, or developer tools.

## Build

On a Mac with Command Line Tools and Python 3.9+:

```sh
python3 macos/build.py
```

The build downloads two pinned, SHA-256-verified Astral runtimes, compiles the
window for Apple Silicon and Intel, signs the app, then creates and verifies
`dist/Trading-Journal-1.0.0-universal.dmg`. Runtime notices are in
`macos/licenses`. The source snapshot is upstream commit `8e9a70c`.

By default the app and DMG are ad-hoc signed. For a Developer ID release, set
`CODE_SIGN_IDENTITY` to your installed Developer ID Application identity when
running the build. The build signs nested code inside out with hardened runtime
and secure timestamps, then signs the app and DMG. The Python executable alone
receives the executable-memory entitlement needed by ctypes/libffi callbacks.

Submit the resulting DMG with `xcrun notarytool submit` using your saved Keychain
profile, wait for an Accepted result, then staple and validate the ticket with
`xcrun stapler`. Generate a fresh SHA-256 checksum after stapling. Keep signing
keys and notarization credentials in Keychain, outside this repository. See
[Apple's notarization documentation](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution).

## Verify

```sh
"dist/Trading Journal.app/Contents/Resources/runtime-arm64/bin/python3" -B macos/test_desktop.py "dist/Trading Journal.app/Contents/Resources/app"
arch -x86_64 "dist/Trading Journal.app/Contents/Resources/runtime-x86_64/bin/python3" -B macos/test_desktop.py "dist/Trading Journal.app/Contents/Resources/app"
```

The Intel check requires an Intel Mac or Rosetta on Apple Silicon. Checks use
disposable data and cover first-run auth, UI assets, port conflicts, a second
app instance, private files, persistence, password reset, and process cleanup.
The existing upstream auth tests can also run with the bundled runtime:

```sh
"dist/Trading Journal.app/Contents/Resources/runtime-arm64/bin/python3" -B tests/run_all.py http_auth preauth_body
```

User state stays under `~/Library/Application Support/Trading Journal`.
Resource symlinks there are refreshed under an exclusive lock each launch,
so app moves and upgrades preserve the journal. Collectors reuse upstream
`unit_runner.py`; quitting stops their process groups before closing the window.
The GUI checks its parent's lifetime so a crashed window also stops services.
No user configuration or state is copied into the distribution.
