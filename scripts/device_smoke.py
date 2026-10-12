"""Install and instrument only a NEW isolated package on a dedicated ARM64 device."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from relocate import PACKAGES

p=argparse.ArgumentParser();p.add_argument('apk',type=Path);p.add_argument('test_apk',type=Path);p.add_argument('--serial',required=True);p.add_argument('--aapt',required=True);p.add_argument('--variant',choices=PACKAGES,default='scroll');p.add_argument('--output',type=Path,required=True);a=p.parse_args()
a.output.mkdir(parents=True,exist_ok=True)
package=PACKAGES[a.variant]
adb=['adb','-s',a.serial]
def call(args,check=True,timeout=30):
    return subprocess.run(adb+args,capture_output=True,text=True,check=check,timeout=timeout).stdout

def badging(apk): return subprocess.check_output([a.aapt,'dump','badging',str(apk)],text=True)
assert f"package: name='{package}'" in badging(a.apk), 'Refuse non-test application APK'
assert f"package: name='{package}.test'" in badging(a.test_apk), 'Refuse unrelated instrumentation APK'
assert 'arm64-v8a' in call(['shell','getprop','ro.product.cpu.abilist'])
assert call(['shell','am','get-current-user']).strip()=='0', 'Fixed-length runtime relocation currently supports user 0 only'
assert not call(['shell','pm','path',package]).strip(), 'Refuse existing test installation; use a clean dedicated test device'
assert not call(['shell','pm','path',package+'.test']).strip(), 'Refuse existing instrumentation installation'
original_before=call(['shell','dumpsys','package','com.winlator'])
try:
    call(['install',str(a.apk)],timeout=120)
    call(['install',str(a.test_apk)],timeout=120)
    for permission in ['READ_EXTERNAL_STORAGE','WRITE_EXTERNAL_STORAGE']:
        call(['shell','pm','grant',package,'android.permission.'+permission])
    run=call(['shell','am','instrument','-w',package+'.test/com.winlator.test.StartupInstrumentation'],check=False,timeout=330)
    (a.output/'instrumentation.txt').write_text(run)
    # Do not clear global logcat or stop/uninstall the original application.
    (a.output/'startup-logcat.txt').write_text(call(['logcat','-d','-v','threadtime','WinlatorStartup:I','WinlatorGuest:I','WinlatorStartupTest:I','*:S']))
    image=subprocess.run(adb+['exec-out','run-as',package,'cat','files/startup-test.png'],capture_output=True)
    if image.returncode==0: (a.output/'startup-test.png').write_bytes(image.stdout)
    assert 'result=PASS' in run and 'desktop=PASS:' in run, 'No successful Windows desktop proof; inspect instrumentation and logcat'
    if a.variant=='scroll': assert 'scroll=PASS:' in run, 'No scrollbar proof'
finally:
    # Stop only the disposable test application, also after a timeout.
    call(['shell','am','force-stop',package],check=False)
    original_after=call(['shell','dumpsys','package','com.winlator'])
    # Compare package registration; dynamic dumpsys fields may change independently.
    def identity(dump): return '\n'.join(line.strip() for line in dump.splitlines() if any(k in line for k in ['versionCode=','versionName=','codePath=','userId=','signatures=']))
    assert identity(original_before)==identity(original_after), 'Original package registration changed'
    (a.output/'original-package-check.json').write_text(json.dumps({'original_registration_unchanged':True,'test_package':package,'apk_sha256':hashlib.sha256(a.apk.read_bytes()).hexdigest()},indent=2))
