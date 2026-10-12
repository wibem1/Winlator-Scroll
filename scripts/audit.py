"""Fail on stale original paths, broken ARM64 loaders or mismatched native inputs."""
import argparse
import hashlib
import io
import json
import struct
import subprocess
import tempfile
import re
import tarfile
import zipfile
from pathlib import Path
import zstandard
from relocate import ORIGINAL, PACKAGES

def interpreter(data):
    if data[:4]!=b'\x7fELF': return None
    assert data[4:6]==b'\x02\x01', 'Unexpected ELF class or endianness'
    off=struct.unpack_from('<Q',data,32)[0]
    size,count=struct.unpack_from('<HH',data,54)
    for i in range(count):
        ph=struct.unpack_from('<IIQQQQQQ',data,off+i*size)
        if ph[0]==3: return data[ph[2]:ph[2]+ph[5]].rstrip(b'\0').decode()
    return None

def audit(entries, package):
    count=0; loaders=[]; failures=[]
    for name,data in entries:
        if name.endswith('.tzst'):
            raw=zstandard.ZstdDecompressor().decompress(data,max_output_size=2**31)
            with tarfile.open(fileobj=io.BytesIO(raw)) as tar:
                members={m.name.lstrip('./') for m in tar}
                for m in tar:
                    label=name+'!'+m.name
                    if ORIGINAL.decode() in m.linkname or any(ORIGINAL.decode() in v for v in m.pax_headers.values()): failures.append(label+': stale link')
                    if not m.isfile(): continue
                    contents=tar.extractfile(m).read(); count+=1
                    if ORIGINAL in contents: failures.append(label+': stale binary/text path')
                    if contents[:4]==b'\x7fELF' and struct.unpack_from('<H',contents,18)[0]==183:
                        path=interpreter(contents)
                        if path:
                            expected='/data/data/'+package+'/files/rootfs/lib/ld-linux-aarch64.so.1'
                            if path!=expected: failures.append(label+': unexpected ARM64 interpreter '+path)
                            loaders.append({'file':label,'interpreter':path})
        else:
            count+=1
            if ORIGINAL in data: failures.append(name+': stale original path')
    assert not failures, '\n'.join(failures)
    assert any('box64' in x['file'] for x in loaders), 'No ARM64 Box64 interpreter audited'
    return {'files_checked':count,'arm64_interpreters':loaders,'stale_original_paths':0}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--variant',choices=PACKAGES,default='scroll');p.add_argument('--apk',type=Path);p.add_argument('--report',type=Path,required=True);a=p.parse_args()
    main=a.root/'app/src/main'
    if a.apk:
        with zipfile.ZipFile(a.apk) as z:
            assert len(z.namelist())==len(set(z.namelist())), 'Duplicate APK entries'
            result=audit([(n,z.read(n)) for n in z.namelist() if n.startswith(('assets/','lib/'))],PACKAGES[a.variant])
            for file in (main/'jniLibs/arm64-v8a').glob('*.so'):
                name='lib/arm64-v8a/'+file.name
                assert z.read(name)==file.read_bytes(), 'Native input changed: '+name
            for file in (main/'assets').rglob('*.tzst'):
                assert z.read('assets/'+str(file.relative_to(main/'assets')))==file.read_bytes(), 'APK archive differs: '+str(file)
            # Validate DT_NEEDED in the actual packaged libraries, not only source inputs.
            platform={'libEGL.so','libGLESv2.so','libGLESv3.so','libOpenSLES.so','libandroid.so','libc.so','libdl.so','libjnigraphics.so','liblog.so','libm.so','libz.so','libvulkan.so','libaaudio.so'}
            libraries={n.rsplit('/',1)[-1]:z.read(n) for n in z.namelist() if n.startswith('lib/arm64-v8a/') and n.endswith('.so')}
            dependencies={}
            with tempfile.TemporaryDirectory() as temp:
                for name,data in libraries.items():
                    assert data[:4]==b'\x7fELF' and struct.unpack_from('<H',data,18)[0]==183, 'Non-ARM64 packaged library: '+name
                    path=Path(temp)/name;path.write_bytes(data)
                    needed=re.findall(r'Shared library: \[(.*?)\]',subprocess.check_output(['readelf','-d',str(path)],text=True))
                    assert not (set(needed)-set(libraries)-platform), 'Missing DT_NEEDED dependency: '+name+': '+str(needed)
                    dependencies[name]=needed
            result['native_dependencies']=dependencies
            result['jni_inputs_byte_identical']=True
            result['apk_sha256']=hashlib.sha256(a.apk.read_bytes()).hexdigest()
    else:
        result=audit([(str(p.relative_to(main)),p.read_bytes()) for p in main.rglob('*') if p.is_file()],PACKAGES[a.variant])
    a.report.write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result,indent=2))
