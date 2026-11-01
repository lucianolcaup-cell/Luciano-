package com.snesflow.android

import android.content.pm.ActivityInfo
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.view.Gravity
import android.view.HapticFeedbackConstants
import android.view.KeyEvent
import android.view.MotionEvent
import android.view.ViewGroup
import android.widget.FrameLayout
import android.widget.TextView
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import com.swordfish.libretrodroid.GLRetroView
import com.swordfish.libretrodroid.GLRetroViewData
import com.swordfish.libretrodroid.ShaderConfig
import com.swordfish.libretrodroid.Variable
import com.swordfish.libretrodroid.ViewportAlignment
import java.io.File
import kotlin.math.roundToInt

class GameActivity : ComponentActivity() {

    companion object {
        const val EXTRA_ROM_PATH = "rom_path"
        private const val X_HOLD_TO_RUN_MS = 90L
        private const val X_TAP_PULSE_MS = 70L
    }

    private lateinit var retroView: GLRetroView
    private lateinit var romFile: File
    private lateinit var sramFile: File
    private lateinit var stateFile: File

    private val uiHandler = Handler(Looper.getMainLooper())
    private var xPressedAt = 0L
    private var xHoldActivated = false
    private var xHoldRunnable: Runnable? = null
    private var xButtonView: TextView? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE
        enableImmersiveMode()

        val path = intent.getStringExtra(EXTRA_ROM_PATH)
        if (path.isNullOrBlank()) return finishWithMessage("ROM não informada.")
        romFile = File(path)
        if (!romFile.isFile) return finishWithMessage("ROM não encontrada.")

        val savesDir = File(filesDir, "saves").apply { mkdirs() }
        val statesDir = File(filesDir, "states").apply { mkdirs() }
        val systemDir = File(filesDir, "system").apply { mkdirs() }
        sramFile = File(savesDir, "${romFile.nameWithoutExtension}.srm")
        stateFile = File(statesDir, "${romFile.nameWithoutExtension}.state")

        val data = GLRetroViewData(this).apply {
            coreFilePath = "snes9x_libretro_android.so"
            gameFilePath = romFile.absolutePath
            systemDirectory = systemDir.absolutePath
            savesDirectory = savesDir.absolutePath
            saveRAMState = sramFile.takeIf { it.isFile }?.readBytes()

            // MASTER HD+ v0.1.7: reconstrução de borda mais forte sem blur analógico.
            shader = ShaderConfig.CUT3(
                useDynamicBlend = true,
                blendMinContrastEdge = 0.01f,
                blendMaxContrastEdge = 0.30f,
                blendMinSharpness = 0.20f,
                blendMaxSharpness = 1.00f,
                staticSharpness = 1.00f,
                edgeUseFastLuma = false,
                softEdgesSharpening = true,
                softEdgesSharpeningAmount = 1.62f,
                hardEdgesSearchMaxError = 0.12f,
                hardEdgesSearchMaxDistance = 8,
            )

            variables = arrayOf(
                Variable("snes9x_aspect", "4:3 scaled"),
                Variable("snes9x_overscan", "auto"),
                Variable("snes9x_gfx_hires", "enabled"),
                Variable("snes9x_hires_blend", "disabled"),
                Variable("snes9x_blargg", "disabled"),
            )

            viewportAlignment = ViewportAlignment.CENTER
            rumbleEventsEnabled = true
            preferLowLatencyAudio = true
            skipDuplicateFrames = false
        }

        retroView = GLRetroView(this, data)
        lifecycle.addObserver(retroView)
        setContentView(buildGameUi())
    }

    private fun buildGameUi(): FrameLayout {
        val root = FrameLayout(this).apply {
            setBackgroundColor(Color.BLACK)
            keepScreenOn = true
            isMotionEventSplittingEnabled = true
        }

        root.addView(
            retroView,
            FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT),
        )

        root.addView(
            TouchControlsView(
                this,
                onKey = { key, pressed -> sendGameKey(key, pressed) },
                onSave = { saveState() },
                onLoad = { loadState() },
            ),
            FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT),
        )

        val xButton = buildSmartXButton()
        xButtonView = xButton
        root.addView(xButton, FrameLayout.LayoutParams(1, 1))

        root.addOnLayoutChangeListener { _, left, top, right, bottom, _, _, _, _ ->
            val width = right - left
            val height = bottom - top
            if (width <= 0 || height <= 0) return@addOnLayoutChangeListener

            val unit = (height * 0.105f).coerceIn(dp(42).toFloat(), dp(78).toFloat())
            val radius = unit * 0.48f
            val size = (radius * 2f).roundToInt()
            val rightX = width * 0.895f
            val baseY = height * 0.73f
            val gap = unit * 0.95f
            val centerX = rightX
            val centerY = baseY - gap

            xButton.layoutParams = FrameLayout.LayoutParams(size, size).apply {
                leftMargin = (centerX - radius).roundToInt()
                topMargin = (centerY - radius).roundToInt()
            }
        }

        return root
    }

    private fun buildSmartXButton(): TextView = TextView(this).apply {
        text = "X"
        setTextColor(Color.WHITE)
        textSize = 20f
        gravity = Gravity.CENTER
        background = faceButtonBackground(false)
        isClickable = true
        isFocusable = true

        setOnTouchListener { view, event ->
            when (event.actionMasked) {
                MotionEvent.ACTION_DOWN -> {
                    cancelXHold()
                    xPressedAt = SystemClock.uptimeMillis()
                    xHoldActivated = false
                    view.background = faceButtonBackground(true)
                    view.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)

                    val hold = Runnable {
                        if (!xHoldActivated) {
                            xHoldActivated = true
                            sendGameKey(KeyEvent.KEYCODE_BUTTON_Y, true)
                        }
                    }
                    xHoldRunnable = hold
                    uiHandler.postDelayed(hold, X_HOLD_TO_RUN_MS)
                    true
                }

                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    val elapsed = SystemClock.uptimeMillis() - xPressedAt
                    cancelXHold()

                    if (xHoldActivated) {
                        sendGameKey(KeyEvent.KEYCODE_BUTTON_Y, false)
                    } else if (event.actionMasked == MotionEvent.ACTION_UP) {
                        // Toque curto preserva a função original do X: arremessar/desmontar.
                        sendGameKey(KeyEvent.KEYCODE_BUTTON_X, true)
                        uiHandler.postDelayed({ sendGameKey(KeyEvent.KEYCODE_BUTTON_X, false) }, X_TAP_PULSE_MS)
                    }

                    xHoldActivated = false
                    view.background = faceButtonBackground(false)
                    true
                }

                else -> true
            }
        }
    }

    private fun cancelXHold() {
        xHoldRunnable?.let(uiHandler::removeCallbacks)
        xHoldRunnable = null
    }

    private fun releaseSmartX() {
        cancelXHold()
        if (xHoldActivated) sendGameKey(KeyEvent.KEYCODE_BUTTON_Y, false)
        xHoldActivated = false
        xButtonView?.background = faceButtonBackground(false)
    }

    private fun sendGameKey(key: Int, pressed: Boolean) {
        retroView.sendKeyEvent(
            if (pressed) KeyEvent.ACTION_DOWN else KeyEvent.ACTION_UP,
            key,
        )
    }

    private fun faceButtonBackground(pressed: Boolean): GradientDrawable = GradientDrawable().apply {
        shape = GradientDrawable.OVAL
        setColor(if (pressed) Color.argb(205, 72, 72, 76) else Color.argb(118, 18, 18, 18))
        setStroke(dp(2), Color.argb(235, 255, 255, 255))
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) enableImmersiveMode()
    }

    override fun onPause() {
        if (::retroView.isInitialized) {
            releaseSmartX()
            saveSramSafely()
        }
        super.onPause()
    }

    override fun onDestroy() {
        releaseSmartX()
        uiHandler.removeCallbacksAndMessages(null)
        super.onDestroy()
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean {
        if (::retroView.isInitialized && isGamepadKey(keyCode)) {
            sendGameKey(keyCode, true)
            return true
        }
        return super.onKeyDown(keyCode, event)
    }

    override fun onKeyUp(keyCode: Int, event: KeyEvent): Boolean {
        if (::retroView.isInitialized && isGamepadKey(keyCode)) {
            sendGameKey(keyCode, false)
            return true
        }
        return super.onKeyUp(keyCode, event)
    }

    private fun saveState() {
        runCatching {
            val state = retroView.serializeState()
            require(state.isNotEmpty()) { "Estado vazio." }
            stateFile.writeBytes(state)
            saveSramSafely()
        }.onSuccess {
            Toast.makeText(this, "Estado salvo.", Toast.LENGTH_SHORT).show()
        }.onFailure {
            Toast.makeText(this, "Falha ao salvar: ${it.message}", Toast.LENGTH_LONG).show()
        }
    }

    private fun loadState() {
        runCatching {
            require(stateFile.isFile) { "Nenhum estado salvo." }
            check(retroView.unserializeState(stateFile.readBytes())) { "O core recusou o estado salvo." }
        }.onSuccess {
            Toast.makeText(this, "Estado carregado.", Toast.LENGTH_SHORT).show()
        }.onFailure {
            Toast.makeText(this, "Falha ao carregar: ${it.message}", Toast.LENGTH_LONG).show()
        }
    }

    private fun saveSramSafely() {
        runCatching {
            val data = retroView.serializeSRAM()
            if (data.isNotEmpty()) sramFile.writeBytes(data)
        }
    }

    private fun finishWithMessage(message: String) {
        Toast.makeText(this, message, Toast.LENGTH_LONG).show()
        finish()
    }

    private fun enableImmersiveMode() {
        WindowCompat.setDecorFitsSystemWindows(window, false)
        WindowInsetsControllerCompat(window, window.decorView).apply {
            hide(WindowInsetsCompat.Type.systemBars())
            systemBarsBehavior = WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
        }
    }

    private fun isGamepadKey(keyCode: Int): Boolean = keyCode in setOf(
        KeyEvent.KEYCODE_DPAD_UP,
        KeyEvent.KEYCODE_DPAD_DOWN,
        KeyEvent.KEYCODE_DPAD_LEFT,
        KeyEvent.KEYCODE_DPAD_RIGHT,
        KeyEvent.KEYCODE_BUTTON_A,
        KeyEvent.KEYCODE_BUTTON_B,
        KeyEvent.KEYCODE_BUTTON_X,
        KeyEvent.KEYCODE_BUTTON_Y,
        KeyEvent.KEYCODE_BUTTON_START,
        KeyEvent.KEYCODE_BUTTON_SELECT,
    )

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).roundToInt()
}
