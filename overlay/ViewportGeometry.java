package com.winlator.core;

/** Android-independent viewport math for fixed-size desktops and IME occlusion. */
public final class ViewportGeometry {
    private ViewportGeometry() {}
    public static int landscapeWidth(int width, int height) {
        int value=Math.max(width,height);
        return value > 0 ? value-(value%2) : 1280;
    }
    public static int landscapeHeight(int width, int height) {
        int value=Math.min(width,height);
        return value > 0 ? value-(value%2) : 720;
    }
    public static int availableHeight(int parentHeight, int topOnScreen, int visibleBottom, int rootHeight, int imeBottom, boolean imeVisible) {
        int available=Math.max(0,Math.min(parentHeight,visibleBottom-topOnScreen));
        if (imeVisible && imeBottom > 0) available=Math.min(available,Math.max(0,rootHeight-imeBottom-topOnScreen));
        return available;
    }
    public static int maximumPan(int desktopHeight, int renderedHeight, int renderedTop, int availableHeight) {
        if (desktopHeight<=0 || renderedHeight<=0) return 0;
        int visible=Math.max(0,Math.min(renderedHeight,availableHeight-renderedTop));
        return Math.max(0,Math.min(desktopHeight,(int)Math.ceil((double)desktopHeight*(renderedHeight-visible)/renderedHeight)));
    }
}
