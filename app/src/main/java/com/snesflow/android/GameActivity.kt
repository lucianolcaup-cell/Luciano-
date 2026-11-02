package com.snesflow.android

import android.content.pm.ActivityInfo
import android.graphics.Color
import android.os.Bundle
import android.view.Gravity
import android.view.KeyEvent
import android.view.View
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
        private const val CREDIT_REVEAL_MS = 1800L
    }

    private lateinit var retroView: GLRetroView
    private lateinit var romFile: File
    private lateinit var sramFile: File
    private lateinit var stateFile: File

    private var controlsView: TouchControlsView? = null
    private var creditShield: View? = null

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

            // Gráfico aprovado da v0.2.0/v0.2.2. Não alterar nesta correção de input.
            shader = ShaderConfig.CUT3(
                useDynamicBlend = true,
                blendMinContrastEdge = 0.00f,
                blendMaxContrastEdge = 0.18f,
                blendMinSharpness = 0.55f,
                blendMaxSharpness = 1.00f,
                staticSharpness = 1.00f,
                edgeUseFastLuma = false,
                softEdgesSharpening = true,
                softEdgesSharpeningAmount = 1.00f,
                hardEdgesSearchMaxError = 0.08f,
                hardEdgesSearchMaxDistance = 10,
            )

            variables = arrayOf(
                Variable("snes9x_aspect", "4:3 scaled"),
                Variable("snes9x_overscan", "auto"),
                Variable("snes9x_gfx_hires", "enabled"),
                Variable("snes9x_hires_blend", "disabled"),
                Variable("snes9x_blargg", "disabled"),
                Variable("snes9x_audio_interpolation", "sinc"),
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

        // v0.2.3: X/A/B/joystick ficam na MESMA View multitouch.
        // Isso permite manter Y (via X segurado) + B simultaneamente para pular carregando objetos.
        val controls = TouchControlsView(
            this,
            onKey = { key, pressed -> sendGameKey(key, pressed) },
            onSave = { saveState() },
            onLoad = { loadState() },
        ).apply {
            visibility = View.INVISIBLE
        }
        controlsView = controls
        root.addView(
            controls,
            FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT),
        )

        val shield = TextView(this).apply {
            text = "Projeto desenvolvido por Bolete, saudações jogadores"
            setTextColor(Color.WHITE)
            textSize = 22f
            gravity = Gravity.CENTER
            setPadding(dp(32), dp(24), dp(32), dp(24))
            setBackgroundColor(Color.BLACK)
            isClickable = true
            isFocusable = true
            importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
        }
        creditShield = shield
        root.addView(
            shield,
            FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT),
        )

        root.postDelayed({
            creditShield?.visibility = View.GONE
            controlsView?.visibility = View.VISIBLE
        }, CREDIT_REVEAL_MS)

        return root
    }

    private fun sendGameKey(key: Int, pressed: Boolean) {
        retroView.sendKeyEvent(
            if (pressed) KeyEvent.ACTION_DOWN else KeyEvent.ACTION_UP,
            key,
        )
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) enableImmersiveMode()
    }

    override fun onPause() {
        if (::retroView.isInitialized) {
            controlsView?.releaseAllInputs()
            saveSramSafely()
        }
        super.onPause()
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
