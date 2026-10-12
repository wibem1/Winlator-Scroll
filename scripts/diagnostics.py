"""Apply shared startup diagnostics; never silently swallow process launch errors."""
from pathlib import Path
import sys
root = Path(sys.argv[1])
src = root/'app/src/main/java/com/winlator'

def edit(file, old, new):
    p=src/file; text=p.read_text()
    if text.count(old)!=1: raise RuntimeError(f'Unexpected upstream anchor: {file}: {old[:60]}')
    p.write_text(text.replace(old,new,1))

edit('core/ProcessHelper.java', 'for (String name : envVars) environment.put(name, envVars.get(name));', 'if (envVars != null) for (String name : envVars) environment.put(name, envVars.get(name));')
edit('core/ProcessHelper.java', '        catch (Exception e) {}\n        return pid;', '''        catch (Exception e) {
            android.util.Log.e("WinlatorStartup", "Process launch failed: "+command, e);
            if (terminationCallback != null) terminationCallback.call(-1);
        }
        return pid;''')
edit('core/ProcessHelper.java', '            java.lang.Process process = processBuilder.start();', '''            android.util.Log.i("WinlatorStartup", "Launching: "+command+" cwd="+workingDir);
            java.lang.Process process = processBuilder.start();''')
edit('core/ProcessHelper.java', '                terminationCallback.call(status);', '''                android.util.Log.i("WinlatorStartup", "Process terminated, status="+status);
                terminationCallback.call(status);''')
edit('XServerDisplayActivity.java', '        if (enableLogs) ProcessHelper.addDebugCallback(debugDialog = new DebugDialog(this));', '''        ProcessHelper.addDebugCallback(line -> android.util.Log.i("WinlatorGuest", line));
        if (enableLogs) ProcessHelper.addDebugCallback(debugDialog = new DebugDialog(this));''')
edit('XServerDisplayActivity.java', '        preloaderDialog.show(R.string.starting_up);', '''        preloaderDialog.show(R.string.starting_up);
        android.util.Log.i("WinlatorStartup", "STARTING package="+getPackageName()+" rootfs="+rootFS.getRootDir());''')
edit('XServerDisplayActivity.java', '                    flags[0] = true;', '''                    flags[0] = true;
                    android.util.Log.i("WinlatorStartup", "FIRST_RENDERABLE_WINDOW class="+window.getClassName());''')
edit('XServerDisplayActivity.java', '        setupUI();', '''        setupUI();
        new android.os.Handler(android.os.Looper.getMainLooper()).postDelayed(() -> {
            if (!flags[0] && !isFinishing() && !isDestroyed()) {
                android.util.Log.e("WinlatorStartup", "START_TIMEOUT: no renderable guest window in 90 seconds");
                preloaderDialog.closeOnUiThread();
                new android.app.AlertDialog.Builder(this)
                    .setTitle("Containerstart fehlgeschlagen")
                    .setMessage("Nach 90 Sekunden wurde kein Windows-Fenster erkannt. Die Testversion wird beendet; die Originalinstallation bleibt unberührt.")
                    .setCancelable(false)
                    .setPositiveButton("Zurück", (dialog, which) -> exit()).show();
            }
        }, 90000);''')
edit('xenvironment/components/GuestProgramLauncherComponent.java', '        envVars.put("BOX64_NOBANNER", box64Logs >= 1 ? "0" : "1");', '''        envVars.put("BOX64_NOBANNER", "0");
        envVars.put("BOX64_LOG", "1");''')
