package com.winlator.widget;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Paint;
import android.graphics.Rect;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.widget.FrameLayout;
import com.winlator.renderer.GLRenderer;

/** A vertical desktop viewport control confined to the area above the IME. */
public final class KeyboardScrollBar extends View {
    private final GLRenderer renderer;
    private final FrameLayout parent;
    private final int desktopHeight;
    private final Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
    private int maximum;
    private int offset;
    private float visibleFraction = 1f;

    public KeyboardScrollBar(Context context, FrameLayout parent, GLRenderer renderer, int desktopHeight) {
        super(context);
        this.parent = parent;
        this.renderer = renderer;
        this.desktopHeight = desktopHeight;
        setTag("keyboard-scrollbar");
        setContentDescription("Windows-Ansicht vertikal verschieben");
        setVisibility(GONE);
        parent.addView(this, new FrameLayout.LayoutParams(dp(40), 1, Gravity.TOP | Gravity.RIGHT));
        parent.getViewTreeObserver().addOnGlobalLayoutListener(this::updateKeyboardBounds);
    }

    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    private void updateKeyboardBounds() {
        Rect visible = new Rect();
        parent.getWindowVisibleDisplayFrame(visible);
        int[] location = new int[2];
        parent.getLocationOnScreen(location);
        int available = Math.max(0, Math.min(parent.getHeight(), visible.bottom - location[1]));
        int hidden = parent.getHeight() - available;
        boolean keyboard = hidden > parent.getRootView().getHeight() * 0.15f;
        renderer.setScreenOffsetYRelativeToCursor(false);
        if (!keyboard) {
            offset = 0;
            maximum = 0;
            renderer.setManualKeyboardPan(false, 0);
            if (getVisibility() != GONE) setVisibility(GONE);
            return;
        }
        // The renderer keeps the full desktop dimensions with adjustNothing.
        int rendered = renderer.isFullscreen() ? parent.getHeight() : renderer.viewTransformation.viewHeight;
        int top = renderer.isFullscreen() ? 0 : renderer.viewTransformation.viewOffsetY;
        int visibleDesktop = Math.max(0, Math.min(rendered, available - top));
        visibleFraction = rendered > 0 ? (float)visibleDesktop / rendered : 1f;
        maximum = Math.max(0, Math.min(desktopHeight, Math.round(desktopHeight * (1f-visibleFraction))));
        offset = Math.min(offset, maximum);
        FrameLayout.LayoutParams params = (FrameLayout.LayoutParams)getLayoutParams();
        int height = Math.max(1, available - dp(16));
        if (params.height != height || params.topMargin != dp(8)) {
            params.height = height;
            params.topMargin = dp(8);
            setLayoutParams(params);
        }
        if (getVisibility() != VISIBLE) setVisibility(VISIBLE);
        renderer.setManualKeyboardPan(true, offset);
        invalidate();
    }

    private float thumbHeight() { return Math.min(getHeight(), Math.max(dp(32), getHeight()*visibleFraction)); }

    @Override protected void onDraw(Canvas canvas) {
        float x = getWidth()/2f;
        paint.setColor(0xCC202830);
        canvas.drawRoundRect(x-dp(8), 0, x+dp(8), getHeight(), dp(8), dp(8), paint);
        float thumb = thumbHeight();
        float y = maximum > 0 ? (getHeight()-thumb)*offset/maximum : 0;
        paint.setColor(0xFFF2BC57);
        canvas.drawRoundRect(x-dp(7), y, x+dp(7), y+thumb, dp(7), dp(7), paint);
    }

    @Override public boolean onTouchEvent(MotionEvent event) {
        switch (event.getActionMasked()) {
            case MotionEvent.ACTION_DOWN:
                getParent().requestDisallowInterceptTouchEvent(true);
            case MotionEvent.ACTION_MOVE:
                float travel = getHeight()-thumbHeight();
                float position = Math.max(0, Math.min(travel, event.getY()-thumbHeight()/2f));
                offset = travel > 0 ? Math.round(maximum*position/travel) : 0;
                renderer.setManualKeyboardPan(true, offset);
                invalidate();
                return true;
            case MotionEvent.ACTION_UP:
                getParent().requestDisallowInterceptTouchEvent(false);
                performClick();
                return true;
            case MotionEvent.ACTION_CANCEL:
                getParent().requestDisallowInterceptTouchEvent(false);
                return true;
            default: return true;
        }
    }
    @Override public boolean performClick() { super.performClick(); return true; }
}
