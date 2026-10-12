# Validation status — 2026-10-12

| Check | Result | What this proves |
| --- | --- | --- |
| Official 11.2 runtime asset comparison | PASS, all 25 `.tzst` assets identical before relocation | Correct official runtime source basis |
| Equal-length relocation / tar regression tests | PASS | Binary offsets, archive modes and symlink metadata preserved |
| Original Box64 negative control | FAIL as expected: cannot open original `/data/data/com.winlator/...` interpreter | Reproduces a definite startup blocker in the former isolated builds |
| Relocated Box64 direct ELF execution under QEMU 8.2 | PASS, Box64 0.4.4 | Corrected ARM64 interpreter and startup chain |
| GLIBC dependency resolution | PASS, all Box64 dependencies found under test package | Native loader resolves relocated libraries |
| Wine through Box64 | PASS, wine-10.10 | Wine userspace executable starts |
| Source/archive audit | PASS, 4411 files, no stale original runtime paths | Source and packed runtime isolation |
| App + device instrumentation compilation | PASS | Both Android APKs compile |
| Final APK audit | PASS, 3607 files, 35 ARM64 libraries | Runtime paths, packaged archives and native dependencies verified |
| Upstream JNI input equality | PASS for all 24 supplied `.so` files | Packaged files exactly match selected upstream inputs |
| APK identity and signature | PASS, `com.wlscroll`, `com.wlscroll.FileProvider`, v2 signature | Separate signed install target; not an actual installation test |
| Android installation | UNVERIFIED | No connected Android device |
| Windows desktop startup on Android | UNVERIFIED | QEMU Linux userspace cannot replace Android's X server / GPU / audio / sandbox |
| Real keyboard and scrollbar on Android | UNVERIFIED | Instrumentation is compiled but has not run on hardware |

Local audited APK SHA-256: `7013b1357200cb61e0cffe6830aa1dd55597c8bb7b598736026eb06bba6a9c0d`. CI APK hashes can differ because debug signing and build paths differ. Machine-readable local results are in `validation/`.

The installed Android Emulator 37.2.12 was probed with an Android 35 ARM64 AVD and software acceleration explicitly selected. It refused to start: `Avd's CPU Architecture 'arm64' is not supported by the QEMU2 emulator on x86_64 host`. KVM acceleration is unavailable as well. A separate Android 35 x86_64 AVD was also started in software mode for a potential partial installation check; it failed to finish booting within the 240-second probe limit, so no installation was attempted. This timeout describes this environment and does not diagnose the Android app.

No Android tablet test has been requested. No original installation has been changed. The isolated test IDs and authority checks block installation over `com.winlator`. A dedicated ARM64/user-0 Android runner is required for the remaining automated installation/desktop/IME checks.

Issues found by the checks and corrected before this result:

- Previous source pin declared Winlator 11.1.
- Source-only substitutions missed embedded ELF interpreters, cache/config data, archived graphics components and absolute symlinks.
- Process launch exceptions were silently swallowed.
- Scroll visibility and range did not reflect actual keyboard occlusion.
- CI's privileged Python lost access to the runner's installed zstandard package; only directory creation now uses elevated privileges.
- Gradle debug-symbol stripping altered supplied native files; explicit per-file preservation now allows exact packaged-input verification.

Successful compilation is **not** a claim that this test version works on the user's tablet.

CI also exposed insufficient Java heap during `compressDebugAssets`. Both variants now set a 3 GiB Gradle heap and limit worker concurrency to two; runtime and APK inputs are unchanged.

Final GitHub Actions run [38236957857](https://github.com/wibem1/Winlator-Scroll/actions/runs/38236957857), source commit `4b72bb9adeb67de581843f466f487b7adbbce142`: **scroll and baseline build/audit jobs both PASS**. Both APK bundles and evidence reports are published as workflow artifacts. The optional ARM64 Android device job was skipped, so installation/desktop/IME remain UNVERIFIED. Subsequent commits only document these results.

## Tablet observation and revision .2

The user subsequently installed revision .1 and supplied a screenshot showing running Wine/Windows windows. This is user evidence that the previous Startup loop is overcome in that attempt. The screenshot shows a portrait-shaped guest desktop inside a landscape screen, no open IME, and Wine's missing-Gecko dialog in front of the file manager. The configured container resolution is unknown; the screenshot alone cannot prove a scrollbar detection failure.

Revision .2 normalizes only `native` resolution to landscape, preserving explicitly configured resolutions. It reads Android 11+ root IME visibility and bottom insets even when `adjustNothing` keeps the surface size fixed. Thirteen executable Java checks cover portrait-to-landscape metrics, unchanged visible-frame/IME occlusion, scaled and letterboxed desktop ranges, and closed-keyboard/zero-size cases. Package `com.wlscrol2` and launcher label `Winlator 11.2 Scroll Test 2` distinguish it from revision .1. A fixed disposable debug signing key allows subsequent updates of this new test package.

Revision .2 Android keyboard behavior remains unverified until observed on a suitable Android device. The Gecko browser engine is not bundled by these viewport changes.

Revision .2 final CI run [38290072119](https://github.com/wibem1/Winlator-Scroll/actions/runs/38290072119), source `9371f2104649b78c2776f8eccfacdb22e0c16e8c`: **both variants PASS**, including all 13 geometry checks, ARM64 Box64/GLIBC/Wine execution, compiled app/instrumentation and final APK audits. The Android device job is skipped. Downloaded scroll APK SHA-256: `810f071903da64ce0dd0ddb0fbc959c2e9f1e7dccadad17a1d10c8f9c9558699`.
