# Winlator 11.2 Scroll Test

Isolated Android experiment: manually move the Windows viewport vertically while the onscreen keyboard is open. The original `com.winlator` application is never an installation target.

## What caused the previous startup failure

The old workflows pinned `c2f4ad4`, which declares **11.1**, not 11.2. Changing only the Android application ID left runtime dependencies pointing into the original application's private directory. In particular, the ARM64 Box64 executable has a `PT_INTERP` entry for `/data/data/com.winlator/files/rootfs/lib/ld-linux-aarch64.so.1`. Android cannot execute that interpreter from a differently owned package. Source-only substitutions did not repair the ELF files, rootfs archives, loader cache, configuration files or absolute symlinks. `ProcessHelper.exec()` also swallowed launch exceptions, leaving the Startup dialog waiting for a guest window that never appeared.

The new basis is official `brunodev85/winlator-app` commit `3981d86efa4f333b2a34a7da8b6521476cd8c8b9`, declaring 11.2/version code 33. All 25 compressed runtime assets were compared byte-for-byte with the official `v11.2.0/Winlator_11.2.apk` before relocation and matched. The public source head includes two subsequent merged fixes; this is a source-built test, not the signed official APK.

## Isolation and relocation

- Scroll package: `com.wlscroll`; comparison package: `com.wlbase00`.
- Both names have exactly the original package ID's byte length. All `/data/data/com.winlator` strings are replaced, including binary strings, compressed tar members, pax link metadata, loader cache, graphics components, and JNI libraries. Binary lengths and internal offsets remain unchanged.
- Java namespace and `Java_com_winlator_*` JNI symbols deliberately remain unchanged. These identify classes, not Android private storage.
- FileProvider uses `${applicationId}.FileProvider` and the matching runtime context package.
- Both variants share the same runtime relocation and diagnostic patches. Only the scroll variant adds viewport control.
- Absolute native paths currently support **Android user 0 only**. Work profiles and secondary users are not supported. Imported/downloaded Wine or graphics components have not been relocated and must not be used in these tests.
- No write, clear, uninstall or force-stop operation targets the original package. The device script refuses pre-existing test installations and compares the original package registration before/after.

The old wildcard `pickFirst '**/*.so'` is removed. Only explicitly named upstream JNI input files may be deduplicated. The APK audit requires their packaged bytes to equal the input bytes, including `libc++_shared.so`. Debug-symbol stripping is disabled for these exact files; a conflicting runtime fails verification rather than silently becoming a test APK.

## Scroll behavior and startup diagnostics

The scrollbar is a vertical touch control wholly above the visible keyboard. Its range follows the actual hidden part of the fitted/fullscreen desktop. The Windows resolution and Android rendering surface remain fixed (`adjustNothing`). The renderer uses manual pan, absolute touch coordinates receive the same offset, and closing the IME resets the viewport. Floating keyboards, magnifier interactions and hardware mouse behavior require device validation.

Guest output and process launch/exit failures are available under `WinlatorStartup` / `WinlatorGuest` in logcat. If no renderable guest window arrives within 90 seconds, the startup overlay closes and offers a return action. This is a diagnostic timeout, not proof that all devices should boot within that time.

## Automatic checks

`Winlator 11.2 audited test build` builds scroll and baseline together from the same pinned source. Every build performs:

1. Relocation regression tests: binary offsets/terminators, archive file modes and pax symlinks.
2. Full source/asset audit, including ARM64 ELF interpreters.
3. **Execution** of relocated ARM64 Box64 via its own ELF interpreter under QEMU, GLIBC dependency resolution, and Wine version execution. This is Linux userspace, not Android desktop validation.
4. APK and instrumentation compilation.
5. APK manifest/package/provider/signature checks, compressed asset equality, JNI input byte equality, and final archive/ELF path audit.

Reports are uploaded even on failure. APK artifacts are uploaded only after all build/audit steps pass. A green build explicitly leaves Android installation, desktop startup and keyboard interaction **UNVERIFIED**.

The optional `device_tests` dispatch input requires a dedicated self-hosted runner with labels `linux`, `ARM64`, `android-test`, Android SDK tools and `WINLATOR_TEST_SERIAL` configured as a repository variable. The script installs only the fresh isolated APKs, grants their storage permissions, runs instrumentation, captures logs and a screenshot, then stops only the test app. Instrumentation installs rootfs, creates a 1280×720 container, requires a real renderable Windows window, opens the real IME, operates the scrollbar, verifies offset and fixed surface size, and verifies reset on closing the IME. A missing device is a blocker, never a passed test.

Local checks (Python 3.12+, zstandard 0.25.0):

```sh
python3 -m unittest discover -s tests -v
python3 scripts/relocate.py upstream-app --variant scroll --report relocation.json
python3 scripts/diagnostics.py upstream-app
python3 patch_winlator.py upstream-app
python3 scripts/audit.py upstream-app --report source-audit.json
# QEMU smoke needs a disposable Linux host and permission to create /data/data/com.wlscroll.
python3 scripts/native_smoke.py upstream-app --report native-smoke.json
```

Do not apply these scripts twice to the same source checkout. Each run starts from the pinned official commit. There is no blanket package rename, no symlink into the original installation, and no original-package build/install shortcut.
