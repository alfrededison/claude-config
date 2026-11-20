// Snippets to copy into an Android instrumented-test source set so recordings made with
// android_record_test.py show touches. Not compiled as-is: keep the part your tests use.
// Each helper logs a TOUCH_TAP / TOUCH_SWIPE line under logcat tag TOUCH, then performs the action.

import android.graphics.Point
import android.util.Log
import android.view.View
import android.view.WindowManager
import androidx.test.espresso.UiController
import androidx.test.espresso.ViewAction
import androidx.test.espresso.action.ViewActions
import androidx.test.espresso.matcher.ViewMatchers
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.uiautomator.UiDevice
import androidx.test.uiautomator.UiObject2
import org.hamcrest.Matcher
import java.util.Locale

object TouchLog {
    /** Full display size in pixels in the current rotation, the space UiDevice and screenrecord use.
     *  Read on every call (not cached) so it stays right after the test rotates the device. */
    private fun screen(): Point {
        val ctx = InstrumentationRegistry.getInstrumentation().context
        @Suppress("DEPRECATION")
        return Point().also { ctx.getSystemService(WindowManager::class.java).defaultDisplay.getRealSize(it) }
    }
    // Plain decimals: Kotlin's Double.toString gives "1.76E9" for epoch seconds, which the parser rejects.
    private fun num(v: Double) = String.format(Locale.US, "%.3f", v)
    private fun now() = num(System.currentTimeMillis() / 1000.0)
    fun tap(x: Float, y: Float) {
        val s = screen()
        Log.i("TOUCH", "TOUCH_TAP ${now()} ${num(x.toDouble())} ${num(y.toDouble())} ${s.x} ${s.y}")
    }
    fun swipe(x1: Float, y1: Float, x2: Float, y2: Float) {
        val s = screen()
        Log.i("TOUCH", "TOUCH_SWIPE ${now()} ${num(x1.toDouble())} ${num(y1.toDouble())} " +
            "${num(x2.toDouble())} ${num(y2.toDouble())} ${s.x} ${s.y}")
    }
}

// MARK: - UiAutomator (works across apps, system UI and keyboards / IMEs)

fun UiDevice.recordedClick(x: Int, y: Int): Boolean {
    TouchLog.tap(x.toFloat(), y.toFloat()); return click(x, y)
}

/** steps: ~5 ms each, as in UiDevice.swipe. */
fun UiDevice.recordedSwipe(x1: Int, y1: Int, x2: Int, y2: Int, steps: Int = 20): Boolean {
    TouchLog.swipe(x1.toFloat(), y1.toFloat(), x2.toFloat(), y2.toFloat()); return swipe(x1, y1, x2, y2, steps)
}

fun UiObject2.recordedClick() {
    val c = visibleCenter; TouchLog.tap(c.x.toFloat(), c.y.toFloat()); click()
}

// MARK: - Espresso: onView(...).perform(recordedClick())

fun recordedClick(): ViewAction = object : ViewAction {
    private val click = ViewActions.click()
    override fun getConstraints(): Matcher<View> = ViewMatchers.isDisplayingAtLeast(90)
    override fun getDescription() = "recorded " + click.description
    override fun perform(uiController: UiController, view: View) {
        val loc = IntArray(2).also(view::getLocationOnScreen)
        TouchLog.tap(loc[0] + view.width / 2f, loc[1] + view.height / 2f)
        click.perform(uiController, view)
    }
}
