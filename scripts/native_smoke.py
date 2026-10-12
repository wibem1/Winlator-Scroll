"""Execute relocated ARM64 userspace via QEMU, not an Android/desktop proof."""
import argparse
import io
import json
import os
import shutil
import subprocess
import tarfile
from pathlib import Path
import zstandard
from relocate import PACKAGES

def extract(asset, destination):
    raw=zstandard.ZstdDecompressor().decompress(asset.read_bytes(),max_output_size=2**31)
    with tarfile.open(fileobj=io.BytesIO(raw)) as t:
        # Trusted pinned archives only; block traversal and out-of-root member names.
        for m in t:
            if m.name.startswith('/') or '..' in Path(m.name).parts: raise ValueError(m.name)
        t.extractall(destination,filter='fully_trusted')
    # Match TarCompressorUtils.extract(), which chmods each extracted file 0771.
    for p in destination.rglob('*'):
        if p.is_file() and not p.is_symlink(): p.chmod(0o771)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--variant',choices=PACKAGES,default='scroll');p.add_argument('--qemu',default='qemu-aarch64');p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    prefix=Path('/data/data')/PACKAGES[a.variant]
    assert not prefix.exists() or not any(prefix.rglob('*')), 'Use a clean, disposable host; refuse existing runtime data'
    destination=prefix/'files/rootfs';destination.mkdir(parents=True,exist_ok=True)
    assets=a.root/'app/src/main/assets'
    try:
        extract(assets/'rootfs.tzst',destination)
        extract(next((assets/'box64').glob('box64-*.tzst')),destination)
        loader=destination/'lib/ld-linux-aarch64.so.1'
        box=destination/'usr/local/bin/box64'
        lib=destination/'usr/lib'
        env=os.environ.copy();env['QEMU_LD_PREFIX']='/';env['BOX64_NOBANNER']='0';env['BOX64_DYNAREC']='0'
        # Use the ELF's own PT_INTERP (no explicit loader command that masks it).
        env['QEMU_SET_ENV']='LD_LIBRARY_PATH='+str(lib)
        # Negative control: the original binary must fail in this relocated rootfs.
        # Never create /data/data/com.winlator to make that binary runnable.
        assert not Path('/data/data/com.winlator').exists(), 'Disposable host must not contain original app data'
        asset=next((assets/'box64').glob('box64-*.tzst'))
        original=subprocess.check_output(['git','-C',str(a.root),'show','HEAD:'+str(asset.relative_to(a.root))])
        raw=zstandard.ZstdDecompressor().decompress(original,max_output_size=2**31)
        with tarfile.open(fileobj=io.BytesIO(raw)) as t:
            original_box=next(m for m in t if m.name.endswith('/box64') and m.isfile())
            control=destination/'usr/local/bin/box64-original-control'
            control.write_bytes(t.extractfile(original_box).read());control.chmod(0o771)
        negative=subprocess.run([a.qemu,str(control),'--version'],env=env,capture_output=True,text=True,timeout=30)
        assert negative.returncode!=0 and '/data/data/com.winlator' in negative.stderr, 'Negative control did not reproduce original ELF loader failure'
        print('NEGATIVE CONTROL: '+negative.stderr.strip(),flush=True)
        commands=[[a.qemu,str(box),'--version'],[a.qemu,str(loader),'--list',str(box)],
                  [a.qemu,str(box),str(destination/'opt/wine/bin/wine'),'--version']]
        results=[]
        for command in commands:
            run=subprocess.run(command,env=env,capture_output=True,text=True,timeout=90)
            results.append({'command':command,'returncode':run.returncode,'stdout':run.stdout,'stderr':run.stderr})
            a.report.write_text(json.dumps({'scope':'ARM64 Linux userspace only; no Android desktop verification','negative_control':{'returncode':negative.returncode,'stderr':negative.stderr},'results':results},indent=2)+'\n')
            print(json.dumps(results[-1],indent=2),flush=True)
            assert run.returncode==0, 'Native smoke failed; see report'
            assert 'not found' not in run.stdout+run.stderr, 'Unresolved runtime library'
    finally:
        shutil.rmtree(prefix)
