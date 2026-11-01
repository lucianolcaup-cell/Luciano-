# DonkeyK2 Android v0.2.1 — ScaleMaster Experimental

Evolução experimental do DonkeyK2 Android com Snes9x e LibretroDroid customizado. A v0.2.0 permanece preservada e não é sobrescrita.

## Controles
- Joystick/D-Pad: movimento, agachar, cordas e portas.
- B: pular.
- A: pegar/colocar parceiro e ações contextuais.
- X toque curto: função original do X (arremessar parceiro/desmontar).
- X segurado: assume a antiga função do Y (correr/rolar/planar com Dixie).
- Select: trocar Kong.
- Start: pausar.
- Y visível e L/R permanecem removidos.
- Triângulo de ação aberto: X acima; A e B afastados abaixo.

## Vídeo — ScaleMaster 4-pass
- Pipeline base CUT3 de três passes preservado para reconstrução direcional de bordas.
- LibretroDroid é clonado em versão fixada e modificado durante o build, sem depender de binário customizado não auditável no repositório.
- Um quarto passe pós-CUT3 aplica sharpening adaptativo por luminância, microcontraste controlado e anti-ringing por clamp da vizinhança 3x3.
- A força é maior em letras, HUD e bordas de alto contraste e menor em áreas suaves, reduzindo halos e granulação nos fundos pré-renderizados de DKC2.
- Snes9x Hi-Res ativado; Blargg/NTSC e Hires Blur desativados; aspecto 4:3 preservado.
- Este perfil NÃO é divulgado como ScaleFX original. O ScaleFX oficial exige uma cadeia de cinco passes com acesso a múltiplos passes anteriores e framebuffers específicos. O ScaleMaster é uma implementação própria adequada às capacidades do renderer atual.

## Áudio — MASTER CLEAN
- Interpolação Snes9x `sinc`.
- Low-latency do LibretroDroid preservado.

## Inicialização
- Crédito do frontend: “Projeto desenvolvido por Bolete, saudações jogadores”.
- `tools/patch_furt_intro.py` restaura somente o salto de boot original que havia sido redirecionado para a tela extra FURT, mantendo a tradução PT-BR.
- O script valida o hook e recalcula o checksum ExHiROM de 6 MiB.

## Ícone
- Launcher usa a mesma arte DonkeyK2 enviada pelo usuário, preparada em 512x512 para o recurso Android `app_icon`.

## Build reproduzível
- CI fixa o LibretroDroid no commit `8835c3098514390a271e36983957f7bb5f40abf1`.
- `tools/patch_libretrodroid_master.py` aplica o quarto passe de forma fail-fast.
- Android SDK 35, CMake 3.22.1, NDK 27 e Gradle 8.9.

## Preservação
A ROM comercial não é mantida no repositório público. O APK privado recebe somente a cópia fornecida pelo usuário na etapa final de empacotamento.

O frontend derivado do LibretroDroid segue GPL-3.0. O core Snes9x possui licença própria com restrições para uso comercial. Projeto destinado a uso pessoal/testes.
