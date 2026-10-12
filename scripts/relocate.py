"""Relocate all runtime paths without changing binary offsets (user 0 test builds)."""
import argparse
import copy
import io
import json
import re
import tarfile
from pathlib import Path
import zstandard

ORIGINAL = b'/data/data/com.winlator'
PACKAGES = {'scroll': 'com.wlscroll', 'baseline': 'com.wlbase00'}
UPSTREAM = '3981d86efa4f333b2a34a7da8b6521476cd8c8b9'

def relocated(data, package):
    target = ('/data/data/' + package).encode()
    if len(target) != len(ORIGINAL) or package not in PACKAGES.values():
        raise ValueError('Only isolated, equal-length test package IDs are permitted')
    return data.replace(ORIGINAL, target)

def archive(data, package):
    raw = zstandard.ZstdDecompressor().decompress(data, max_output_size=2**31)
    output = io.BytesIO()
    count = 0
    with tarfile.open(fileobj=io.BytesIO(raw)) as src, tarfile.open(fileobj=output, mode='w', format=tarfile.PAX_FORMAT) as dst:
        for member in src:
            m = copy.copy(member)
            count += member.linkname.encode().count(ORIGINAL)
            m.linkname = relocated(member.linkname.encode(), package).decode()
            m.pax_headers = {k: relocated(v.encode(), package).decode() for k, v in member.pax_headers.items()}
            contents = src.extractfile(member).read() if member.isfile() else None
            if contents is not None:
                count += contents.count(ORIGINAL)
                changed = relocated(contents, package)
                assert len(changed) == len(contents)
                m.size = len(changed)
                dst.addfile(m, io.BytesIO(changed))
            else:
                dst.addfile(m)
    return (zstandard.ZstdCompressor(level=10).compress(output.getvalue()) if count else data), count

def prepare(root, variant):
    package = PACKAGES[variant]
    main = root / 'app/src/main'
    report = {'upstream': UPSTREAM, 'package': package, 'files': {}}
    for p in sorted(main.rglob('*')):
        if not p.is_file():
            continue
        data = p.read_bytes()
        if p.suffix == '.tzst':
            changed, count = archive(data, package)
        else:
            count = data.count(ORIGINAL)
            changed = relocated(data, package)
        if count:
            p.write_bytes(changed)
            report['files'][str(p.relative_to(root))] = count
    manifest = main / 'AndroidManifest.xml'
    data = manifest.read_text()
    assert data.count('com.winlator.FileProvider') == 1
    manifest.write_text(data.replace('com.winlator.FileProvider', '${applicationId}.FileProvider'))
    utils = main / 'java/com/winlator/core/FileUtils.java'
    data = utils.read_text()
    assert data.count('"com.winlator.FileProvider"') == 1
    utils.write_text(data.replace('"com.winlator.FileProvider"', 'activity.getPackageName()+".FileProvider"'))
    gradle = root / 'app/build.gradle'
    data = gradle.read_text().replace("applicationId 'com.winlator'", f"applicationId '{package}'")
    data = data.replace('versionName "11.2"', f'versionName "11.2-{variant}.1"')
    # Imported CMake libraries are the same inputs as jniLibs. Only allow these
    # known collisions; APK audit compares their bytes with the declared inputs.
    names = sorted(p.name for p in (main/'jniLibs/arm64-v8a').glob('*.so'))
    options = '\n    packagingOptions {\n        jniLibs {\n            pickFirsts += [' + ', '.join(repr('lib/arm64-v8a/'+n) for n in names) + ']\n        }\n    }\n'
    data = data.replace("    ndkVersion '24.0.8215888'", options + "    ndkVersion '24.0.8215888'")
    data = data.replace('        versionCode 33', '        versionCode 33001\n        testInstrumentationRunner "com.winlator.test.StartupInstrumentation"')
    # Keep reflection-based instrumentation usable and make this a diagnostic build.
    data = data.replace('minifyEnabled true', 'minifyEnabled false')
    gradle.write_text(data)
    test = root/'app/src/androidTest/java/com/winlator/test/StartupInstrumentation.java'
    test.parent.mkdir(parents=True,exist_ok=True)
    test.write_text((Path(__file__).resolve().parents[1]/'overlay/StartupInstrumentation.java').read_text())
    strings = main/'res/values/strings.xml'
    text = strings.read_text()
    text, count = re.subn(r'(<string name="app_name">).*?(</string>)', rf'\g<1>Winlator 11.2 {variant.title()} Test\g<2>', text)
    assert count == 1
    strings.write_text(text)
    return report

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('root', type=Path)
    p.add_argument('--variant', choices=PACKAGES, default='scroll')
    p.add_argument('--report', type=Path, required=True)
    a = p.parse_args()
    a.report.write_text(json.dumps(prepare(a.root, a.variant), indent=2)+'\n')
