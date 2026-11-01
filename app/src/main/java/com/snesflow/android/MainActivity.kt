package com.snesflow.android

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.OpenableColumns
import android.view.Gravity
import android.view.ViewGroup
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.result.contract.ActivityResultContracts
import java.io.File
import java.io.FileOutputStream
import java.io.InputStream

class MainActivity : ComponentActivity() {

    companion object {
        private const val PREFS = "snes_flow"
        private const val KEY_ACTIVE_ROM = "active_rom"
        private const val BUNDLED_ASSET = "dkc2.sfc"
        private const val BUNDLED_NAME = "Donkey_Kong_Country_2.sfc"
        private const val MAX_ROM_BYTES = 32L * 1024L * 1024L
        private val ROM_EXTENSIONS = setOf("sfc", "smc", "fig")
    }

    private lateinit var status: TextView
    private lateinit var playButton: Button
    private val prefs by lazy { getSharedPreferences(PREFS, MODE_PRIVATE) }

    private val romPicker = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) importRom(uri)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        prepareBundledRomIfPresent()
        setContentView(buildUi())
        refreshUi()
    }

    private fun buildUi(): LinearLayout = LinearLayout(this).apply {
        orientation = LinearLayout.VERTICAL
        gravity = Gravity.CENTER_HORIZONTAL
        setPadding(dp(24), dp(30), dp(24), dp(24))

        addView(TextView(this@MainActivity).apply {
            text = "SNES Flow HD"
            textSize = 31f
            gravity = Gravity.CENTER
        }, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))

        addView(TextView(this@MainActivity).apply {
            text = "Donkey Kong Country 2 • controles touch • filtro HD • tela imersiva"
            textSize = 16f
            gravity = Gravity.CENTER
            setPadding(0, dp(12), 0, dp(18))
        })

        status = TextView(this@MainActivity).apply {
            textSize = 15f
            gravity = Gravity.CENTER
            setPadding(dp(8), dp(12), dp(8), dp(18))
        }
        addView(status, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))

        playButton = actionButton("JOGAR DONKEY KONG 2") { launchActiveRom() }.apply { textSize = 20f }
        addView(playButton)

        addView(actionButton("Importar outra ROM") {
            romPicker.launch(arrayOf("application/octet-stream", "*/*"))
        })
    }

    private fun prepareBundledRomIfPresent() {
        runCatching {
            val dir = File(filesDir, "roms").apply { mkdirs() }
            val destination = File(dir, BUNDLED_NAME)
            if (!destination.isFile || destination.length() == 0L) {
                assets.open(BUNDLED_ASSET).use { input ->
                    FileOutputStream(destination).use { output -> input.copyTo(output) }
                }
            }
            require(destination.length() in 1..MAX_ROM_BYTES) { "ROM integrada inválida." }
            prefs.edit().putString(KEY_ACTIVE_ROM, destination.absolutePath).apply()
        }
    }

    private fun launchActiveRom() {
        val path = prefs.getString(KEY_ACTIVE_ROM, null)
        if (path != null && File(path).isFile) {
            startActivity(Intent(this, GameActivity::class.java).putExtra(GameActivity.EXTRA_ROM_PATH, path))
        } else {
            Toast.makeText(this, "Nenhuma ROM disponível.", Toast.LENGTH_SHORT).show()
        }
    }

    private fun importRom(uri: Uri) {
        runCatching {
            val displayName = queryDisplayName(uri) ?: "jogo.sfc"
            val extension = displayName.substringAfterLast('.', "").lowercase()
            require(extension in ROM_EXTENSIONS) { "Formato não suportado. Use .sfc, .smc ou .fig." }
            val dir = File(filesDir, "roms").apply { mkdirs() }
            val destination = File(dir, "importada_${System.currentTimeMillis()}.$extension")
            contentResolver.openInputStream(uri).use { input ->
                requireNotNull(input) { "Não foi possível abrir a ROM." }
                copyWithLimit(input, destination, MAX_ROM_BYTES)
            }
            prefs.edit().putString(KEY_ACTIVE_ROM, destination.absolutePath).apply()
        }.onSuccess {
            Toast.makeText(this, "ROM importada.", Toast.LENGTH_SHORT).show()
            refreshUi()
        }.onFailure {
            Toast.makeText(this, it.message ?: "Falha ao importar ROM.", Toast.LENGTH_LONG).show()
        }
    }

    private fun refreshUi() {
        val active = prefs.getString(KEY_ACTIVE_ROM, null)?.let(::File)?.takeIf { it.isFile }
        status.text = if (active != null) "Pronto para jogar • ${active.name}" else "APK sem ROM integrada: importe uma ROM para testar."
        playButton.isEnabled = active != null
    }

    private fun actionButton(label: String, action: () -> Unit): Button = Button(this).apply {
        text = label
        isAllCaps = false
        setOnClickListener { action() }
        layoutParams = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(60)).apply { topMargin = dp(9) }
    }

    private fun queryDisplayName(uri: Uri): String? {
        contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor ->
            val index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (index >= 0 && cursor.moveToFirst()) return cursor.getString(index)
        }
        return null
    }

    private fun copyWithLimit(input: InputStream, destination: File, limit: Long) {
        FileOutputStream(destination).use { output ->
            val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
            var total = 0L
            while (true) {
                val read = input.read(buffer)
                if (read < 0) break
                total += read
                require(total <= limit) { "Arquivo excede o limite permitido." }
                output.write(buffer, 0, read)
            }
        }
        require(destination.length() > 0L) { "Arquivo vazio." }
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}
