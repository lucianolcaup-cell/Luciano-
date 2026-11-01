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
        private const val MIN_Y_PRESS_MS = 110L
    }

    private lateinit var retroView: GLRetroView
    private lateinit var romFile: File
    private lateinit var sramFile: File
    private lateinit var stateFile: File

    private val uiHandler = Handler(Looper.getMainLooper())
    private var yPressed = false
    private var yPressedAt = 0L
    private var pendingYRelease: Runnable? = null
    private var yButtonView: TextView? = null

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

            // MASTER HD: upscale forte sem borrar o pixel art nem deformar 4:3.
            shader = ShaderConfig.CUT3(
                useDynamicBlend = true,
                blendMinContrastEdge = 0.02f,
                blendMaxContrastEdge = 0.38f,
                blendMinSharpness = 0.10f,
                blendMaxSharpness = 0.95f,
                staticSharpness = 0.98f,
                edgeUseFastLuma = false,
                softEdgesSharpening = true,
                softEdgesSharpeningAmount = 1.42f,
                hardEdgesSearchMaxError = 0.18f,
                hardEdgesSearchMaxDistance = 6,
            )

            // Mantém a fonte do SNES limpa antes do shader.
            variables = arrayOf(
                Variable("snes9x_aspect", "4:3"),
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

        val yButton = buildDedicatedYButton()
        yButtonView = yButton
        root.addView(yButton, FrameLayout.LayoutParams(1, 1))

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
            val centerX = rightX - gap
            val centerY = baseY

            yButton.layoutParams = FrameLayout.LayoutParams(size, size).apply {
                leftMargin = (centerX - radius).roundToInt()
                topMargin = (centerY - radius).roundToInt()
            }
        }

        return root
    }

    private fun buildDedicatedYButton(): TextView = TextView(this).apply {
        text = "Y"
        setTextColor(Color.WHITE)
        textSize = 20f
        gravity = Gravity.CENTER
        background = faceButtonBackground(false)
        isClickable = true
        isFocusable = true

        setOnTouchListener { view, event ->
            when (event.actionMasked) {
                MotionEvent.ACTION_DOWN -> {
                    pendingYRelease?.let(uiHandler::removeCallbacks)
                    pendingYRelease = null
                    if (!yPressed) {
                        yPressed = true
                        yPressedAt = SystemClock.uptimeMillis()
                        sendGameKey(KeyEvent.KEYCODE_BUTTON_Y, true)
                        view.background = faceButtonBackground(true)
                        view.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)
                    }
                    true
                }

                MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> {
                    releaseYWithMinimumPulse()
                    true
                }

                else -> true
            }
        }
    }

    private fun releaseYWithMinimumPulse() {
        if (!yPressed) return
        pendingYRelease?.let(uiHandler::removeCallbacks)

        val elapsed = SystemClock.uptimeMillis() - yPressedAt
        val remaining = (MIN_Y_PRESS_MS - elapsed).coerceAtLeast(0L)
        val release = Runnable { releaseYNow() }
        pendingYRelease = release
        uiHandler.postDelayed(release, remaining)
    }

    private fun releaseYNow() {
        pendingYRelease?.let(uiHandler::removeCallbacks)
        pendingYRelease = null
        if (!yPressed) return
        yPressed = false
        sendGameKey(KeyEvent.KEYCODE_BUTTON_Y, false)
        yButtonView?.background = faceButtonBackground(false)
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
            releaseYNow()
            saveSramSafely()
        }
        super.onPause()
    }

    override fun onDestroy() {
        releaseYNow()
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
