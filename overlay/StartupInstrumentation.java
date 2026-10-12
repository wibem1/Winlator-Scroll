package com.winlator.test;

import android.app.Activity;
import android.app.Instrumentation;
import android.content.Intent;
import android.os.Bundle;
import android.os.SystemClock;
import android.view.MotionEvent;
import android.view.View;
import android.view.inputmethod.InputMethodManager;
import com.winlator.MainActivity;
import com.winlator.XServerDisplayActivity;
import com.winlator.container.Container;
import com.winlator.container.ContainerManager;
import com.winlator.core.AppUtils;
import com.winlator.xenvironment.RootFS;
import com.winlator.xserver.Window;
import org.json.JSONObject;
import java.lang.reflect.Method;
import java.util.concurrent.atomic.AtomicBoolean;

/** Opt-in test on a dedicated ARM64 Android device; never targets com.winlator. */
public final class StartupInstrumentation extends Instrumentation {
    private Bundle arguments;
    @Override public void onCreate(Bundle args) { arguments=args; start(); }
    private interface Condition { boolean ready() throws Exception; }
    private void waitFor(String label, Condition condition, long millis) throws Exception {
        long limit=SystemClock.elapsedRealtime()+millis;
        do {
            if (condition.ready()) return;
            SystemClock.sleep(250);
        } while (SystemClock.elapsedRealtime()<limit);
        throw new IllegalStateException("Timed out: "+label);
    }
    private boolean hasDesktopWindow(Window window) {
        if (window.isRenderable() && window.isDesktopWindow()) return true;
        for (Window child: window.getChildren()) if (hasDesktopWindow(child)) return true;
        return false;
    }
    @Override public void onStart() {
        Bundle result=new Bundle();
        try {
            String pkg=getTargetContext().getPackageName();
            if (!pkg.equals("com.wlscroll") && !pkg.equals("com.wlbase00")) throw new SecurityException("Not an isolated test package");
            Intent main=new Intent(getTargetContext(), MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            Activity activity=startActivitySync(main);
            waitFor("rootfs installation", () -> RootFS.find(getTargetContext()).isValid(), 180000);
            ContainerManager manager=new ContainerManager(getTargetContext());
            Method create=ContainerManager.class.getDeclaredMethod("createContainer", JSONObject.class);
            create.setAccessible(true);
            JSONObject data=new JSONObject(); data.put("name", "Automated Startup Test"); data.put("screenSize", "1280x720");
            Container container=(Container)create.invoke(manager,data);
            if (container==null) throw new IllegalStateException("Container creation failed");
            Intent intent=new Intent(getTargetContext(), XServerDisplayActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            intent.putExtra("container_id",container.id);
            XServerDisplayActivity desktop=(XServerDisplayActivity)startActivitySync(intent);
            waitFor("renderable Windows desktop window", () -> desktop.getXServer()!=null && hasDesktopWindow(desktop.getXServer().windowManager.rootWindow), 85000);
            result.putString("desktop", "PASS: renderable Windows desktop window detected");
            // Obtain a real framebuffer image as evidence for review.
            android.graphics.Bitmap screenshot=getUiAutomation().takeScreenshot();
            if (screenshot==null) throw new IllegalStateException("No screenshot");
            try (java.io.FileOutputStream stream=getTargetContext().openFileOutput("startup-test.png",0)) {
                screenshot.compress(android.graphics.Bitmap.CompressFormat.PNG,100,stream);
            }
            if (pkg.equals("com.wlscroll")) {
                int width=desktop.getXServerView().getWidth(), height=desktop.getXServerView().getHeight();
                runOnMainSync(() -> AppUtils.showKeyboard(desktop));
                waitFor("visible keyboard scrollbar", () -> {
                    AtomicBoolean visible=new AtomicBoolean();
                    runOnMainSync(() -> { View bar=desktop.getWindow().getDecorView().findViewWithTag("keyboard-scrollbar"); visible.set(bar!=null && bar.getVisibility()==View.VISIBLE); });
                    return visible.get();
                },10000);
                if (width!=desktop.getXServerView().getWidth() || height!=desktop.getXServerView().getHeight()) throw new IllegalStateException("IME resized the desktop");
                runOnMainSync(() -> {
                    View bar=desktop.getWindow().getDecorView().findViewWithTag("keyboard-scrollbar");
                    long now=SystemClock.uptimeMillis();
                    MotionEvent down=MotionEvent.obtain(now,now,MotionEvent.ACTION_DOWN,bar.getWidth()/2f,bar.getHeight()-1f,0);
                    bar.dispatchTouchEvent(down);down.recycle();
                    MotionEvent up=MotionEvent.obtain(now,now+20,MotionEvent.ACTION_UP,bar.getWidth()/2f,bar.getHeight()-1f,0);
                    bar.dispatchTouchEvent(up);up.recycle();
                });
                if (desktop.getXServerView().getRenderer().getKeyboardPanY()<=0) throw new IllegalStateException("Scrollbar did not move viewport");
                runOnMainSync(() -> ((InputMethodManager)desktop.getSystemService(Activity.INPUT_METHOD_SERVICE)).hideSoftInputFromWindow(desktop.getWindow().getDecorView().getWindowToken(),0));
                waitFor("viewport reset after IME close", () -> desktop.getXServerView().getRenderer().getKeyboardPanY()==0,10000);
                result.putString("scroll", "PASS: IME, control input, offset, fixed desktop size and reset");
            }
            runOnMainSync(desktop::finish);
            runOnMainSync(activity::finish);
            result.putString("result", "PASS");finish(Activity.RESULT_OK,result);
        } catch (Throwable error) {
            android.util.Log.e("WinlatorStartupTest", "FAIL", error);
            result.putString("result", "FAIL: "+android.util.Log.getStackTraceString(error));finish(Activity.RESULT_CANCELED,result);
        }
    }
}
