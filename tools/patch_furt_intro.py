#!/usr/bin/env python3
"""Remove apenas a tela inicial extra do patch FURT em uma ROM DKC2 PT-BR já traduzida.

Não contém ROM nem dados comerciais. O script exige a ROM privada já patchada pelo usuário,
valida o hook conhecido e restaura o fluxo original de boot. Também recalcula o checksum
ExHiROM de 6 MiB.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

ROM_SIZE = 0x600000
HOOK_OFFSET = 0x00B6BA
HOOK_FURT = bytes.fromhex("5c000050")      # JML $50:0000 (rotina extra do patch)
HOOK_ORIGINAL = bytes.fromhex("5cef8580")  # JML $80:85EF (fluxo original)
EXHIROM_HEADER = 0x40FFC0
CHECKSUM_OFFSET = EXHIROM_HEADER + 0x1C


def mirror_checksum_6m(data: bytearray) -> int:
    if len(data) != ROM_SIZE:
        raise ValueError(f"ROM deve ter 6 MiB; tamanho recebido: {len(data)} bytes")

    working = bytearray(data)
    working[CHECKSUM_OFFSET:CHECKSUM_OFFSET + 4] = b"\xFF\xFF\x00\x00"

    # Em uma imagem ExHiROM de 6 MiB, os 2 MiB finais são espelhados para completar 8 MiB.
    return (sum(working[:0x400000]) + 2 * sum(working[0x400000:0x600000])) & 0xFFFF


def patch_rom(source: Path, destination: Path) -> tuple[str, str, int]:
    data = bytearray(source.read_bytes())
    before_sha = hashlib.sha256(data).hexdigest()

    if len(data) != ROM_SIZE:
        raise ValueError(f"ROM incompatível: esperado {ROM_SIZE} bytes, recebido {len(data)}")

    if data[EXHIROM_HEADER + 0x15] != 0x35:
        raise ValueError("ROM incompatível: cabeçalho ExHiROM/FastROM 0x35 não encontrado")

    current_hook = bytes(data[HOOK_OFFSET:HOOK_OFFSET + 4])
    if current_hook == HOOK_ORIGINAL:
        raise ValueError("A tela FURT já está removida nesta ROM")
    if current_hook != HOOK_FURT:
        raise ValueError(
            "ROM incompatível: hook esperado não encontrado; operação abortada para evitar corrupção"
        )

    data[HOOK_OFFSET:HOOK_OFFSET + 4] = HOOK_ORIGINAL

    checksum = mirror_checksum_6m(data)
    complement = checksum ^ 0xFFFF
    data[CHECKSUM_OFFSET:CHECKSUM_OFFSET + 2] = complement.to_bytes(2, "little")
    data[CHECKSUM_OFFSET + 2:CHECKSUM_OFFSET + 4] = checksum.to_bytes(2, "little")

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)

    after_sha = hashlib.sha256(data).hexdigest()
    return before_sha, after_sha, checksum


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="ROM PT-BR FURT privada de 6 MiB")
    parser.add_argument("destination", type=Path, help="arquivo de saída")
    args = parser.parse_args()

    before_sha, after_sha, checksum = patch_rom(args.source, args.destination)
    print(f"SHA-256 entrada : {before_sha}")
    print(f"SHA-256 saída   : {after_sha}")
    print(f"Checksum SNES   : {checksum:04X}")
    print("Hook de intro removido com sucesso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
