package com.snesflow.android

object IpsPatcher {
    private const val MAX_OUTPUT_SIZE = 32 * 1024 * 1024

    fun apply(original: ByteArray, patch: ByteArray): ByteArray {
        require(patch.size >= 8) { "Patch IPS inválido: arquivo muito pequeno." }
        require(String(patch, 0, 5, Charsets.US_ASCII) == "PATCH") {
            "Patch IPS inválido: cabeçalho PATCH ausente."
        }

        var output = original.copyOf()
        var cursor = 5

        while (true) {
            require(cursor + 3 <= patch.size) { "Patch IPS truncado." }

            if (patch[cursor] == 'E'.code.toByte() &&
                patch[cursor + 1] == 'O'.code.toByte() &&
                patch[cursor + 2] == 'F'.code.toByte()
            ) {
                cursor += 3
                break
            }

            val offset = read24(patch, cursor)
            cursor += 3
            require(cursor + 2 <= patch.size) { "Patch IPS truncado no tamanho do registro." }

            val size = read16(patch, cursor)
            cursor += 2

            if (size == 0) {
                require(cursor + 3 <= patch.size) { "Patch IPS truncado no registro RLE." }
                val runLength = read16(patch, cursor)
                cursor += 2
                val value = patch[cursor]
                cursor += 1
                require(runLength > 0) { "Patch IPS contém RLE vazio." }
                output = ensureCapacity(output, offset + runLength)
                output.fill(value, offset, offset + runLength)
            } else {
                require(cursor + size <= patch.size) { "Patch IPS truncado nos dados do registro." }
                output = ensureCapacity(output, offset + size)
                patch.copyInto(output, offset, cursor, cursor + size)
                cursor += size
            }
        }

        if (cursor + 3 == patch.size) {
            val truncateSize = read24(patch, cursor)
            require(truncateSize in 1..MAX_OUTPUT_SIZE) { "Tamanho final IPS inválido." }
            output = output.copyOf(truncateSize)
        } else {
            require(cursor == patch.size) { "Dados extras inesperados após EOF do patch IPS." }
        }

        return output
    }

    private fun ensureCapacity(input: ByteArray, required: Int): ByteArray {
        require(required in 0..MAX_OUTPUT_SIZE) { "Patch excede o limite seguro de 32 MiB." }
        return if (required <= input.size) input else input.copyOf(required)
    }

    private fun read16(data: ByteArray, index: Int): Int =
        ((data[index].toInt() and 0xFF) shl 8) or (data[index + 1].toInt() and 0xFF)

    private fun read24(data: ByteArray, index: Int): Int =
        ((data[index].toInt() and 0xFF) shl 16) or
            ((data[index + 1].toInt() and 0xFF) shl 8) or
            (data[index + 2].toInt() and 0xFF)
}
