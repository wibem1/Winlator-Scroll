from pathlib import Path
import sys
root=Path(sys.argv[1])
src=root/"app/src/main/java/com/winlator"
def edit(path, old, new):
    p=src/path
    data=p.read_text()
    if data.count(old)!=1:
        raise RuntimeError(f"Patch failed in {path}: {old[:80]!r} (count {data.count(old)})")
    p.write_text(data.replace(old,new,1))
r="renderer/GLRenderer.java"
edit(r,"    private boolean screenOffsetYRelativeToCursor = false;", """    private boolean screenOffsetYRelativeToCursor = false;
    private volatile boolean manualKeyboardPan = false;
    private volatile int keyboardPanY = 0;""")
edit(r,"        float pointerX = 0;\n        float pointerY = 0;", """        float pointerX = 0;
        float pointerY = 0;
        boolean manualPan = manualKeyboardPan;""")
edit(r,"if (screenOffsetYRelativeToCursor || magnifierZoom != 1.0f) {", "if (!manualPan && (screenOffsetYRelativeToCursor || magnifierZoom != 1.0f)) {")
edit(r,"        XForm.makeTransform(tmpXForm2, -pointerX, -pointerY, magnifierZoom, magnifierZoom, 0);", """        if (manualPan) pointerY = keyboardPanY;
        XForm.makeTransform(tmpXForm2, -pointerX, -pointerY, magnifierZoom, magnifierZoom, 0);""")
edit(r,"    public boolean isScreenOffsetYRelativeToCursor() {", """    public void setManualKeyboardPan(boolean enabled, int offset) {
        manualKeyboardPan = enabled;
        keyboardPanY = enabled ? Math.max(0, offset) : 0;
        xServerView.requestRender();
    }
    public int getKeyboardPanY() {
        return manualKeyboardPan ? keyboardPanY : 0;
    }
    public boolean isScreenOffsetYRelativeToCursor() {""")
r="widget/TouchpadView.java"
edit(r,"            this.x = this.startX = this.lastX = (int)transformedPoint[0];", """            transformedPoint[1] += xServer.getRenderer().getKeyboardPanY();
            this.x = this.startX = this.lastX = (int)transformedPoint[0];""")
edit(r,"            this.x = (int)transformedPoint[0];", """            transformedPoint[1] += xServer.getRenderer().getKeyboardPanY();
            this.x = (int)transformedPoint[0];""")
edit(r,"                    if (isEnabled()) xServer.injectPointerMove((int)transformedPoint[0], (int)transformedPoint[1]);", """                    transformedPoint[1] += xServer.getRenderer().getKeyboardPanY();
                    if (isEnabled()) xServer.injectPointerMove((int)transformedPoint[0], (int)transformedPoint[1]);""")
edit(r,"                    xServer.injectPointerMove((int)transformedPoint[0], (int)transformedPoint[1]);\n                    handled = true;", """                    transformedPoint[1] += xServer.getRenderer().getKeyboardPanY();
                    xServer.injectPointerMove((int)transformedPoint[0], (int)transformedPoint[1]);
                    handled = true;""")
r="XServerDisplayActivity.java"
edit(r,"import android.view.View;", """import android.view.View;
import android.view.Gravity;
import android.widget.SeekBar;
import android.util.TypedValue;""")
edit(r,"        AppUtils.observeSoftKeyboardVisibility(drawerLayout, renderer::setScreenOffsetYRelativeToCursor);", """        // Overlay does not resize the Windows desktop.
        final SeekBar keyboardScroll = new SeekBar(this);
        keyboardScroll.setRotation(90f);
        keyboardScroll.setMax(Math.max(1, xServer.screenInfo.height / 2));
        keyboardScroll.setVisibility(View.GONE);
        int length = (int) TypedValue.applyDimension(
                TypedValue.COMPLEX_UNIT_DIP, 240, getResources().getDisplayMetrics());
        int thickness = (int) TypedValue.applyDimension(
                TypedValue.COMPLEX_UNIT_DIP, 44, getResources().getDisplayMetrics());
        FrameLayout.LayoutParams params = new FrameLayout.LayoutParams(length, thickness);
        params.gravity = Gravity.RIGHT | Gravity.CENTER_VERTICAL;
        keyboardScroll.setTranslationX(-(length - thickness) / 2f);
        rootView.addView(keyboardScroll, params);
        keyboardScroll.setOnSeekBarChangeListener(new SeekBar.OnSeekBarChangeListener() {
            @Override public void onProgressChanged(SeekBar bar, int value, boolean fromUser) {
                renderer.setManualKeyboardPan(true, value);
            }
            @Override public void onStartTrackingTouch(SeekBar bar) {}
            @Override public void onStopTrackingTouch(SeekBar bar) {}
        });
        AppUtils.observeSoftKeyboardVisibility(drawerLayout, visible -> {
            renderer.setScreenOffsetYRelativeToCursor(false);
            renderer.setManualKeyboardPan(visible, visible ? keyboardScroll.getProgress() : 0);
            keyboardScroll.setVisibility(visible ? View.VISIBLE : View.GONE);
            if (!visible) keyboardScroll.setProgress(0);
        });""")
print("Patched Winlator app sources")

# FileProvider authority must be unique for parallel installation.
manifest=root/"app/src/main/AndroidManifest.xml"
ms=manifest.read_text()
assert ms.count('android:authorities="com.winlator.FileProvider"') == 1
manifest.write_text(ms.replace('android:authorities="com.winlator.FileProvider"', 'android:authorities="com.winlator.scrolltest.FileProvider"'))
edit("core/FileUtils.java", '"com.winlator.FileProvider"', '"com.winlator.scrolltest.FileProvider"')
print("Applied unique FileProvider authority for side-by-side installation")
