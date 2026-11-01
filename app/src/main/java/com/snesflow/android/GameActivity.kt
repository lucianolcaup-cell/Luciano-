package com.snesflow.android

import android.content.pm.ActivityInfo
import android.graphics.Color
import android.os.Bundle
import android.view.KeyEvent
import android.view.ViewGroup
import android.widget.FrameLayout
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import com.swordfish.libretrodroid.GLRetroView
import com.swordfish.libretrodroid.GLRetroViewData
import com.swordfish.libretrodroid.ShaderConfig
import com.swordfish.libretrodroid.ViewportAlignment
import java.io.File

class GameActivity : ComponentActivity() {

    companion object { const val EXTRA_ROM_PATH = "rom_path" }

    private lateinit var retroView: GLRetroView
    private lateinit var romFile: File
    private lateinit var sramFile: File
    private lateinit var stateFile: File

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
            shader = ShaderConfig.CUT3(
                staticSharpness = 0.88f,
                softEdgesSharpeningAmount = 1.22f,
                hardEdgesSearchMaxDistance = 4,
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

    private fun buildGameUi(): FrameLayout = FrameLayout(this).apply {
        setBackgroundColor(Color.BLACK)
        keepScreenOn = true

        addView(retroView, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))
        addView(
            TouchControlsView(
                this@GameActivity,
                onKey = { key, pressed ->
                    retroView.sendKeyEvent(if (pressed) KeyEvent.ACTION_DOWN else KeyEvent.ACTION_UP, key)
                },
                onSave = { saveState() },
                onLoad = { loadState() },
            ),
            FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT),
        )
    }

    override fun onWindowFocusChanged(hasFocus: Boolean) {
        super.onWindowFocusChanged(hasFocus)
        if (hasFocus) enableImmersiveMode()
    }

    override fun onPause() {
        if (::retroView.isInitialized) saveSramSafely()
        super.onPause()
    }

    override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean {
        if (::retroView.isInitialized && isGamepadKey(keyCode)) {
            retroView.sendKeyEvent(KeyEvent.ACTION_DOWN, keyCode)
            return true
        }
        return super.onKeyDown(keyCode, event)
    }

    override fun onKeyUp(keyCode: Int, event: KeyEvent): Boolean {
        if (::retroView.isInitialized && isGamepadKey(keyCode)) {
            retroView.sendKeyEvent(KeyEvent.ACTION_UP, keyCode)
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
}
