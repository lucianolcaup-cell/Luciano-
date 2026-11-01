# DonkeyK2 Android v0.2.0

Build privado Android com Snes9x/LibretroDroid.

## Controles
- Joystick/D-Pad: movimento, agachar, cordas e portas.
- B: pular.
- A: pegar/colocar parceiro e ações contextuais.
- X toque curto: função original do X (arremessar parceiro/desmontar).
- X segurado: assume a antiga função do Y (correr/rolar/planar com Dixie).
- Select: trocar Kong.
- Start: pausar.
- Y visível e L/R permanecem removidos.
- Triângulo de ação mais aberto: X acima; A e B mais afastados abaixo.

## Vídeo — MASTER HD+ TEXT
- Snes9x Hi-Res ativado.
- Blargg/NTSC e Hires Blur desativados.
- Aspecto 4:3 preservado.
- CUT3 recalibrado dentro das faixas válidas para maior definição de letras, HUD e bordas de sprites.
- Busca de bordas ampliada e sharpening de soft edges limitado a 1.00.

## Áudio — MASTER CLEAN
- Interpolação de áudio Snes9x configurada em `sinc`.
- Low-latency do LibretroDroid preservado para manter resposta rápida aos comandos.

## Inicialização
- O crédito do frontend é exibido brevemente: “Projeto desenvolvido por Bolete, saudações jogadores”.
- A tela adicional do patch FURT não é mais tratada por temporizador.
- Na montagem privada, `tools/patch_furt_intro.py` restaura somente o salto de boot original (`JML $80:85EF`) que havia sido redirecionado para a rotina extra em `$50:0000`, mantendo o restante da tradução PT-BR intacto.
- O script valida o hook antes de alterar a ROM e recalcula o checksum ExHiROM de 6 MiB.

## Preservação
A ROM comercial não é mantida no repositório público. A build privada recebe apenas a cópia fornecida pelo usuário durante a etapa final de empacotamento.

O frontend usa LibretroDroid (GPL-3.0). O core Snes9x possui licença própria com restrições para uso comercial. Projeto destinado a uso pessoal/testes.
