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
import java.security.MessageDigest

class MainActivity : ComponentActivity() {

    companion object {
        private const val PREFS = "snes_flow"
        private const val KEY_ACTIVE_ROM = "active_rom"
        private const val KEY_ORIGINAL_ROM = "original_rom"
        private const val KEY_PATCHED_ROM = "patched_rom"
        private const val MAX_ROM_BYTES = 32L * 1024L * 1024L
        private const val MAX_PATCH_BYTES = 4L * 1024L * 1024L
        val ROM_EXTENSIONS = setOf("sfc", "smc", "fig")
    }

    private lateinit var status: TextView
    private lateinit var playButton: Button
    private lateinit var useOriginalButton: Button
    private lateinit var usePatchedButton: Button

    private val prefs by lazy { getSharedPreferences(PREFS, MODE_PRIVATE) }

    private val romPicker = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) importRom(uri)
    }

    private val patchPicker = registerForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) importIpsPatch(uri)
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(buildUi())
        refreshUi()
    }

    private fun buildUi(): LinearLayout {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER_HORIZONTAL
            setPadding(dp(24), dp(28), dp(24), dp(24))
        }

        root.addView(TextView(this).apply {
            text = "SNES Flow"
            textSize = 30f
            gravity = Gravity.CENTER
        }, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))

        root.addView(TextView(this).apply {
            text = "Importe sua ROM de Super Nintendo. O jogo não é incluído no aplicativo."
            textSize = 16f
            gravity = Gravity.CENTER
            setPadding(0, dp(12), 0, dp(18))
        })

        status = TextView(this).apply {
            textSize = 15f
            gravity = Gravity.CENTER
            setPadding(dp(8), dp(12), dp(8), dp(18))
        }
        root.addView(status, LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT))

        root.addView(actionButton("Importar ROM (.sfc/.smc)") {
            romPicker.launch(arrayOf("application/octet-stream", "*/*"))
        })

        root.addView(actionButton("Importar tradução (.ips)") {
            patchPicker.launch(arrayOf("application/octet-stream", "*/*"))
        })

        useOriginalButton = actionButton("Usar ROM original") {
            prefs.getString(KEY_ORIGINAL_ROM, null)?.let {
                prefs.edit().putString(KEY_ACTIVE_ROM, it).apply()
                refreshUi()
            }
        }
        root.addView(useOriginalButton)

        usePatchedButton = actionButton("Usar ROM traduzida") {
            prefs.getString(KEY_PATCHED_ROM, null)?.let {
                prefs.edit().putString(KEY_ACTIVE_ROM, it).apply()
                refreshUi()
            }
        }
        root.addView(usePatchedButton)

        playButton = actionButton("JOGAR") {
            val path = prefs.getString(KEY_ACTIVE_ROM, null)
            if (path != null && File(path).isFile) {
                startActivity(Intent(this, GameActivity::class.java).putExtra(GameActivity.EXTRA_ROM_PATH, path))
            } else {
                Toast.makeText(this, "Importe uma ROM válida primeiro.", Toast.LENGTH_SHORT).show()
            }
        }.apply {
            textSize = 20f
        }
        root.addView(playButton)

        return root
    }

    private fun actionButton(label: String, action: () -> Unit): Button = Button(this).apply {
        text = label
        isAllCaps = false
        setOnClickListener { action() }
        layoutParams = LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, dp(58)).apply {
            topMargin = dp(8)
        }
    }

    private fun importRom(uri: Uri) {
        runCatching {
            val displayName = queryDisplayName(uri) ?: "jogo.sfc"
            val extension = displayName.substringAfterLast('.', "").lowercase()
            require(extension in ROM_EXTENSIONS) { "Formato não suportado. Use .sfc, .smc ou .fig." }

            val romDir = File(filesDir, "roms").apply { mkdirs() }
            val safeName = sanitizeFileName(displayName)
            val destination = uniqueFile(romDir, safeName)
            contentResolver.openInputStream(uri).use { input ->
                requireNotNull(input) { "Não foi possível abrir a ROM." }
                copyWithLimit(input, destination, MAX_ROM_BYTES)
            }

            val sha = sha256(destination)
            prefs.edit()
                .putString(KEY_ORIGINAL_ROM, destination.absolutePath)
                .putString(KEY_ACTIVE_ROM, destination.absolutePath)
                .remove(KEY_PATCHED_ROM)
                .apply()

            "ROM importada: ${destination.name}\nSHA-256: ${sha.take(16)}…"
        }.onSuccess {
            Toast.makeText(this, "ROM importada.", Toast.LENGTH_SHORT).show()
            refreshUi(extraStatus = it)
        }.onFailure {
            Toast.makeText(this, it.message ?: "Falha ao importar ROM.", Toast.LENGTH_LONG).show()
        }
    }

    private fun importIpsPatch(uri: Uri) {
        runCatching {
            val originalPath = prefs.getString(KEY_ORIGINAL_ROM, null)
                ?: error("Importe a ROM original antes do patch.")
            val originalFile = File(originalPath)
            require(originalFile.isFile) { "ROM original não encontrada." }

            val displayName = queryDisplayName(uri) ?: "traducao.ips"
            require(displayName.substringAfterLast('.', "").equals("ips", ignoreCase = true)) {
                "Nesta versão, o patch de tradução deve ser .ips."
            }

            val patchBytes = contentResolver.openInputStream(uri).use { input ->
                requireNotNull(input) { "Não foi possível abrir o patch." }
                readWithLimit(input, MAX_PATCH_BYTES)
            }
            val patched = IpsPatcher.apply(originalFile.readBytes(), patchBytes)

            val output = File(originalFile.parentFile, "traduzida_${originalFile.nameWithoutExtension}.sfc")
            output.writeBytes(patched)
            prefs.edit()
                .putString(KEY_PATCHED_ROM, output.absolutePath)
                .putString(KEY_ACTIVE_ROM, output.absolutePath)
                .apply()

            "Tradução IPS aplicada: ${output.name}\nSHA-256: ${sha256(output).take(16)}…"
        }.onSuccess {
            Toast.makeText(this, "Patch aplicado. ROM traduzida selecionada.", Toast.LENGTH_LONG).show()
            refreshUi(extraStatus = it)
        }.onFailure {
            Toast.makeText(this, it.message ?: "Falha ao aplicar patch.", Toast.LENGTH_LONG).show()
        }
    }

    private fun refreshUi(extraStatus: String? = null) {
        val original = prefs.getString(KEY_ORIGINAL_ROM, null)?.let(::File)?.takeIf { it.isFile }
        val patched = prefs.getString(KEY_PATCHED_ROM, null)?.let(::File)?.takeIf { it.isFile }
        val active = prefs.getString(KEY_ACTIVE_ROM, null)?.let(::File)?.takeIf { it.isFile }

        status.text = extraStatus ?: when {
            active == null -> "Nenhuma ROM importada."
            patched != null && active.absolutePath == patched.absolutePath -> "Selecionada: ${patched.name} (traduzida)"
            else -> "Selecionada: ${active.name}"
        }

        playButton.isEnabled = active != null
        useOriginalButton.isEnabled = original != null && active?.absolutePath != original.absolutePath
        usePatchedButton.isEnabled = patched != null && active?.absolutePath != patched.absolutePath
    }

    private fun queryDisplayName(uri: Uri): String? {
        contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { cursor ->
            val index = cursor.getColumnIndex(OpenableColumns.DISPLAY_NAME)
            if (index >= 0 && cursor.moveToFirst()) return cursor.getString(index)
        }
        return null
    }

    private fun sanitizeFileName(name: String): String {
        val clean = name.replace(Regex("[^A-Za-z0-9._ -]"), "_").trim()
        return clean.take(120).ifBlank { "jogo.sfc" }
    }

    private fun uniqueFile(dir: File, name: String): File {
        val base = name.substringBeforeLast('.', name)
        val ext = name.substringAfterLast('.', "")
        var candidate = File(dir, name)
        var n = 1
        while (candidate.exists()) {
            candidate = File(dir, if (ext.isBlank()) "${base}_$n" else "${base}_$n.$ext")
            n++
        }
        return candidate
    }

    private fun copyWithLimit(input: InputStream, destination: File, limit: Long) {
        FileOutputStream(destination).use { output ->
            val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
            var total = 0L
            while (true) {
                val read = input.read(buffer)
                if (read < 0) break
                total += read
                require(total <= limit) { "Arquivo excede o limite de ${limit / 1024 / 1024} MiB." }
                output.write(buffer, 0, read)
            }
        }
        require(destination.length() > 0) { "Arquivo vazio." }
    }

    private fun readWithLimit(input: InputStream, limit: Long): ByteArray {
        val output = java.io.ByteArrayOutputStream()
        val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
        var total = 0L
        while (true) {
            val read = input.read(buffer)
            if (read < 0) break
            total += read
            require(total <= limit) { "Arquivo excede o limite de ${limit / 1024 / 1024} MiB." }
            output.write(buffer, 0, read)
        }
        return output.toByteArray()
    }

    private fun sha256(file: File): String {
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
            while (true) {
                val read = input.read(buffer)
                if (read < 0) break
                digest.update(buffer, 0, read)
            }
        }
        return digest.digest().joinToString("") { "%02x".format(it) }
    }

    private fun dp(value: Int): Int = (value * resources.displayMetrics.density).toInt()
}
