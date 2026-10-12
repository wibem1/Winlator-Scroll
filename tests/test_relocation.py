import io
import sys
import tarfile
import unittest
from pathlib import Path
import zstandard
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from relocate import ORIGINAL, archive, relocated

class RelocationTests(unittest.TestCase):
    def test_binary_offsets_and_terminators(self):
        old = b'\x7fELF\x00'+ORIGINAL+b'/files/rootfs/lib/ld-linux-aarch64.so.1\x00\x01\xff'
        result = relocated(old, 'com.wlscroll')
        self.assertEqual(len(old), len(result))
        self.assertEqual(result.replace(b'/data/data/com.wlscroll', ORIGINAL), old)
        self.assertNotIn(ORIGINAL, result)
        with self.assertRaises(ValueError): relocated(old, 'com.winlator.scrolltest2')
        with self.assertRaises(ValueError): relocated(old, 'com.winlator')

    def test_archive_preserves_binary_mode_and_links(self):
        out = io.BytesIO()
        with tarfile.open(fileobj=out, mode='w', format=tarfile.PAX_FORMAT) as t:
            m = tarfile.TarInfo('box64'); m.mode=0o755
            d = ORIGINAL+b'/files/rootfs\0'; m.size=len(d); t.addfile(m, io.BytesIO(d))
            m = tarfile.TarInfo('z:'); m.type=tarfile.SYMTYPE; m.linkname=ORIGINAL.decode()+'/files/rootfs'
            m.pax_headers={'linkpath':m.linkname}; t.addfile(m)
        packed = zstandard.ZstdCompressor().compress(out.getvalue())
        result, count = archive(packed, 'com.wlscroll')
        self.assertEqual(count, 2)
        with tarfile.open(fileobj=io.BytesIO(zstandard.ZstdDecompressor().decompress(result))) as t:
            self.assertEqual(t.getmember('box64').mode, 0o755)
            self.assertEqual(t.getmember('z:').linkname, '/data/data/com.wlscroll/files/rootfs')
            self.assertNotIn(ORIGINAL, t.extractfile('box64').read())
        self.assertEqual(archive(result, 'com.wlscroll'), (result, 0))

if __name__=='__main__': unittest.main()
