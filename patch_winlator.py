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
    private volatile int keyboardPanY = -1;""")
edit(r,"        float pointerX = 0;\n        float pointerY = 0;", """        float pointerX = 0;
        float pointerY = 0;
        int panY = keyboardPanY;\n        boolean manualPan = panY >= 0;""")
edit(r,"if (screenOffsetYRelativeToCursor || magnifierZoom != 1.0f) {", "if (!manualPan && (screenOffsetYRelativeToCursor || magnifierZoom != 1.0f)) {")
edit(r,"        XForm.makeTransform(tmpXForm2, -pointerX, -pointerY, magnifierZoom, magnifierZoom, 0);", """        if (manualPan) pointerY = panY;
        XForm.makeTransform(tmpXForm2, -pointerX, -pointerY, magnifierZoom, magnifierZoom, 0);""")
edit(r,"    public boolean isScreenOffsetYRelativeToCursor() {", """    public void setManualKeyboardPan(boolean enabled, int offset) {
        keyboardPanY = enabled ? Math.min(xServer.screenInfo.height, Math.max(0, offset)) : -1;
        xServerView.requestRender();
    }
    public int getKeyboardPanY() {
        return Math.max(0, keyboardPanY);
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
edit(r,"        AppUtils.observeSoftKeyboardVisibility(drawerLayout, renderer::setScreenOffsetYRelativeToCursor);", """        getWindow().setSoftInputMode(android.view.WindowManager.LayoutParams.SOFT_INPUT_ADJUST_NOTHING);
        new com.winlator.widget.KeyboardScrollBar(this, rootView, renderer, xServer.screenInfo.height);""")
(src / "widget/KeyboardScrollBar.java").write_text((Path(__file__).parent / "overlay/KeyboardScrollBar.java").read_text())
print("Patched manual keyboard viewport control")
edit("renderer/GLRenderer.java", "float magnifierZoom = !screenOffsetYRelativeToCursor ? this.magnifierZoom : 1.0f;", "float magnifierZoom = !manualPan && !screenOffsetYRelativeToCursor ? this.magnifierZoom : 1.0f;")
