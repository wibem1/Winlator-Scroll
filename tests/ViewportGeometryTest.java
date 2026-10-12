import com.winlator.core.ViewportGeometry;

public final class ViewportGeometryTest {
    private static void equal(int expected,int actual,String label) {
        if (expected!=actual) throw new AssertionError(label+": expected "+expected+", got "+actual);
    }
    public static void main(String[] args) {
        equal(1920,ViewportGeometry.landscapeWidth(1200,1920),"portrait metrics before activity rotation");
        equal(1200,ViewportGeometry.landscapeHeight(1200,1920),"portrait metrics height");
        equal(1920,ViewportGeometry.landscapeWidth(1921,1201),"even native width");
        equal(1200,ViewportGeometry.landscapeHeight(1921,1201),"even native height");
        equal(700,ViewportGeometry.availableHeight(1200,0,1200,1200,500,true),"adjustNothing: visible frame stays full but IME occludes 500 pixels");
        equal(1200,ViewportGeometry.availableHeight(1200,0,1200,1200,500,false),"closed keyboard ignores stale inset");
        equal(660,ViewportGeometry.availableHeight(1160,40,1200,1200,500,true),"screen-to-parent coordinates");
        equal(700,ViewportGeometry.availableHeight(1200,0,700,1200,0,false),"legacy visible-frame fallback");
        equal(300,ViewportGeometry.maximumPan(720,1200,0,700),"scaled landscape desktop lower edge");
        equal(350,ViewportGeometry.maximumPan(900,900,150,700),"letterboxed desktop lower edge");
        equal(0,ViewportGeometry.maximumPan(720,900,150,1200),"closed keyboard has no pan");
        equal(720,ViewportGeometry.maximumPan(720,900,150,100),"fully occluded desktop is clamped");
        equal(0,ViewportGeometry.maximumPan(720,0,0,700),"renderer not initialized");
        System.out.println("PASS: native landscape and IME viewport geometry (13 checks)");
    }
}
