package com.snesflow.android

import android.content.pm.ActivityInfo
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.view.Gravity
import android.view.KeyEvent
import android.view.MotionEvent
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.FrameLayout
import android.widget.GridLayout
import android.widget.LinearLayout
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

    companion object {
        const val EXTRA_ROM_PATH = "rom_path"
    }

    private lateinit var retroView: GLRetroView
    private lateinit var romFile: File
    private lateinit var sramFile: File
    private lateinit var stateFile: File

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE
        enableImmersiveMode()

        val path = intent.getStringExtra(EXTRA_ROM_PATH)
        if (path.isNullOrBlank()) {
            finishWithMessage("ROM não informada.")
            return
        }

        romFile = File(path)
        if (!romFile.isFile) {
            finishWithMessage("ROM não encontrada.")
            return
        }

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
            shader = ShaderConfig.Default
            viewportAlignment = ViewportAlignment.CENTER
            rumbleEventsEnabled = true
            preferLowLatencyAudio = true
            skipDuplicateFrames = false
        }

        retroView = GLRetroView(this, data)
        lifecycle.addObserver(retroView)
        setContentView(buildGameUi())
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

    private fun buildGameUi(): FrameLayout {
        val root = FrameLayout(this).apply {
            setBackgroundColor(Color.BLACK)
            keepScreenOn = true
        }

        root.addView(retroView, FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT))

        root.addView(buildDPad(), FrameLayout.LayoutParams(dp(220), dp(220)).apply {
            gravity = Gravity.START or Gravity.BOTTOM
            leftMargin = dp(18)
            bottomMargin = dp(16)
        })

        root.addView(buildActionPad(), FrameLayout.LayoutParams(dp(220), dp(220)).apply {
            gravity = Gravity.END or Gravity.BOTTOM
            rightMargin = dp(18)
            bottomMargin = dp(16)
        })

        root.addView(buildShoulderBar(), FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(58)).apply {
            gravity = Gravity.TOP
            leftMargin = dp(18)
            rightMargin = dp(18)
            topMargin = dp(10)
        })

        root.addView(buildCenterBar(), FrameLayout.LayoutParams(dp(330), dp(56)).apply {
            gravity = Gravity.CENTER_HORIZONTAL or Gravity.BOTTOM
            bottomMargin = dp(26)
        })

        return root
    }

    private fun buildDPad(): GridLayout = GridLayout(this).apply {
        rowCount = 3
        columnCount = 3
        addPadButton(this, "↑", KeyEvent.KEYCODE_DPAD_UP, 0, 1)
        addPadButton(this, "←", KeyEvent.KEYCODE_DPAD_LEFT, 1, 0)
        addPadButton(this, "→", KeyEvent.KEYCODE_DPAD_RIGHT, 1, 2)
        addPadButton(this, "↓", KeyEvent.KEYCODE_DPAD_DOWN, 2, 1)
    }

    private fun buildActionPad(): GridLayout = GridLayout(this).apply {
        rowCount = 3
        columnCount = 3
        addPadButton(this, "X", KeyEvent.KEYCODE_BUTTON_X, 0, 1)
        addPadButton(this, "Y", KeyEvent.KEYCODE_BUTTON_Y, 1, 0)
        addPadButton(this, "A", KeyEvent.KEYCODE_BUTTON_A, 1, 2)
        addPadButton(this, "B", KeyEvent.KEYCODE_BUTTON_B, 2, 1)
    }

    private fun addPadButton(grid: GridLayout, label: String, keyCode: Int, row: Int, column: Int) {
        val button = gameButton(label, keyCode)
        val size = dp(70)
        button.layoutParams = GridLayout.LayoutParams(GridLayout.spec(row, 1, 1f), GridLayout.spec(column, 1, 1f)).apply {
            width = size
            height = size
            setMargins(dp(2), dp(2), dp(2), dp(2))
        }
        grid.addView(button)
    }

    private fun buildShoulderBar(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.HORIZONTAL
        gravity = Gravity.CENTER_VERTICAL
        addView(gameButton("L", KeyEvent.KEYCODE_BUTTON_L1), LinearLayout.LayoutParams(dp(96), dp(50)))
        addView(View(this@GameActivity), LinearLayout.LayoutParams(0, dp(1), 1f))
        addView(gameButton("R", KeyEvent.KEYCODE_BUTTON_R1), LinearLayout.LayoutParams(dp(96), dp(50)))
    }

    private fun buildCenterBar(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.HORIZONTAL
        gravity = Gravity.CENTER
        addView(gameButton("SELECT", KeyEvent.KEYCODE_BUTTON_SELECT), LinearLayout.LayoutParams(dp(82), dp(48)).apply { rightMargin = dp(5) })
        addView(menuButton("SALVAR") { saveState() }, LinearLayout.LayoutParams(dp(78), dp(48)).apply { rightMargin = dp(5) })
        addView(menuButton("CARREGAR") { loadState() }, LinearLayout.LayoutParams(dp(88), dp(48)).apply { rightMargin = dp(5) })
        addView(gameButton("START", KeyEvent.KEYCODE_BUTTON_START), LinearLayout.LayoutParams(dp(82), dp(48)))
    }

    private fun gameButton(label: String, keyCode: Int): Button = baseButton(label).apply {
        setOnTouchListener { _, event ->
            when (event.actionMasked) {
                MotionEvent.ACTION_DOWN, MotionEvent.ACTION_POINTER_DOWN -> {
                    retroView.sendKeyEvent(KeyEvent.ACTION_DOWN, keyCode)
                    isPressed = true
                    true
                }
                MotionEvent.ACTION_UP, MotionEvent.ACTION_POINTER_UP, MotionEvent.ACTION_CANCEL -> {
                    retroView.sendKeyEvent(KeyEvent.ACTION_UP, keyCode)
                    isPressed = false
                    true
                }
                else -> true
            }
        }
    }

    private fun menuButton(label: String, action: () -> Unit): Button = baseButton(label).apply {
        setOnClickListener { action() }
    }

    private fun baseButton(label: String): Button = Button(this).apply {
        text = label
        isAllCaps = false
        textSize = 14f
        setTextColor(Color.WHITE)
        alpha = 0.72f
        background = GradientDrawable().apply {
            shape = GradientDrawable.RECTANGLE
            cornerRadius = dp(18).toFloat()
            setColor(Color.argb(180, 35, 35, 35))
            setStroke(dp(1), Color.argb(210, 255, 255, 255))
        }
        setPadding(dp(4), 0, dp(4), 0)
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
        KeyEvent.KEYCODE_DPAD_UP, KeyEvent.KEYCODE_DPAD_DOWN, KeyEvent.KEYCODE_DPAD_LEFT, KeyEvent.KEYCODE_DPAD_RIGHT,
        KeyEvent.KEYCODE_BUTTON_A, KeyEvent.KEYCODE_BUTTON_B, KeyEvent.KEYCODE_BUTTON_X, KeyEvent.KEYCODE_BUTTON_Y,
        KeyEvent.KEYCODE_BUTTON_L1, KeyEvent.KEYCODE_BUTTON_R1, KeyEvent.KEYCODE_BUTTON_START, KeyEvent.KEYCODE_BUTTON_SELECT
    )

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}
