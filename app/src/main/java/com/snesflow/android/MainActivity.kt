package com.snesflow.android

import android.content.Intent
import android.os.Bundle
import android.widget.Toast
import androidx.activity.ComponentActivity
import java.io.File
import java.io.FileOutputStream

class MainActivity : ComponentActivity() {

    companion object {
        private const val BUNDLED_ASSET = "dkc2.sfc"
        private const val BUNDLED_NAME = "DonkeyK2_PTBR_v1.sfc"
        private const val MAX_ROM_BYTES = 32L * 1024L * 1024L
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.decorView.setBackgroundColor(android.graphics.Color.BLACK)

        val rom = runCatching { prepareBundledRom() }.getOrElse {
            Toast.makeText(this, "Falha ao preparar o jogo: ${it.message}", Toast.LENGTH_LONG).show()
            finish()
            return
        }

        startActivity(
            Intent(this, GameActivity::class.java)
                .putExtra(GameActivity.EXTRA_ROM_PATH, rom.absolutePath)
        )
        finish()
    }

    private fun prepareBundledRom(): File {
        val dir = File(filesDir, "roms").apply { mkdirs() }
        val destination = File(dir, BUNDLED_NAME)

        if (!destination.isFile || destination.length() == 0L) {
            assets.open(BUNDLED_ASSET).use { input ->
                FileOutputStream(destination).use { output ->
                    val buffer = ByteArray(DEFAULT_BUFFER_SIZE)
                    var total = 0L
                    while (true) {
                        val read = input.read(buffer)
                        if (read < 0) break
                        total += read
                        require(total <= MAX_ROM_BYTES) { "ROM integrada excede o limite permitido." }
                        output.write(buffer, 0, read)
                    }
                }
            }
        }

        require(destination.length() in 1..MAX_ROM_BYTES) { "ROM integrada inválida." }
        return destination
    }
}
