#!/usr/bin/env python3
from pathlib import Path

ROOT = Path("vendor/LibretroDroid")
CPP = ROOT / "libretrodroid/src/main/cpp/shadermanager.cpp"
GRADLE = ROOT / "libretrodroid/build.gradle"

if not CPP.is_file():
    raise SystemExit(f"LibretroDroid não encontrado: {CPP}")

source = CPP.read_text(encoding="utf-8")

marker = "ShaderManager::Chain ShaderManager::getShader(const ShaderManager::Config& config) {"
if marker not in source:
    raise SystemExit("Ponto de inserção do ShaderManager não encontrado")

master_shader = r'''
// DonkeyK2 ScaleMaster v0.2.1
// Quarto passe pós-CUT3: sharpen adaptativo em luminância com anti-ringing.
// Mantém cores/contornos do pixel art e evita halos em texto/HUD.
const std::string donkeyMasterVertex = R"GLSL(
#ifdef GL_FRAGMENT_PRECISION_HIGH
#define HIGHP highp
#else
#define HIGHP mediump
precision mediump float;
#endif
attribute vec4 vPosition;
attribute vec2 vCoordinate;
uniform HIGHP vec2 textureSize;
varying HIGHP vec2 coords;
varying HIGHP vec2 texel;
void main() {
    coords = vCoordinate;
    texel = vec2(1.0) / textureSize;
    gl_Position = vPosition;
}
)GLSL";

const std::string donkeyMasterFragment = R"GLSL(
#ifdef GL_FRAGMENT_PRECISION_HIGH
#define HIGHP highp
#else
#define HIGHP mediump
precision mediump float;
#endif
uniform lowp sampler2D previousPass;
varying HIGHP vec2 coords;
varying HIGHP vec2 texel;

mediump float luma(mediump vec3 c) {
    return dot(c, vec3(0.2126, 0.7152, 0.0722));
}

void main() {
    mediump vec3 c  = texture2D(previousPass, coords).rgb;
    mediump vec3 l  = texture2D(previousPass, coords - vec2(texel.x, 0.0)).rgb;
    mediump vec3 r  = texture2D(previousPass, coords + vec2(texel.x, 0.0)).rgb;
    mediump vec3 u  = texture2D(previousPass, coords - vec2(0.0, texel.y)).rgb;
    mediump vec3 d  = texture2D(previousPass, coords + vec2(0.0, texel.y)).rgb;
    mediump vec3 ul = texture2D(previousPass, coords - texel).rgb;
    mediump vec3 ur = texture2D(previousPass, coords + vec2(texel.x, -texel.y)).rgb;
    mediump vec3 dl = texture2D(previousPass, coords + vec2(-texel.x, texel.y)).rgb;
    mediump vec3 dr = texture2D(previousPass, coords + texel).rgb;

    mediump vec3 crossAvg = (l + r + u + d) * 0.25;
    mediump vec3 diagAvg  = (ul + ur + dl + dr) * 0.25;
    mediump vec3 localAvg = mix(crossAvg, diagAvg, 0.18);

    mediump float lc = luma(c);
    mediump float edge = max(
        max(abs(lc - luma(l)), abs(lc - luma(r))),
        max(abs(lc - luma(u)), abs(lc - luma(d)))
    );
    mediump float diagEdge = max(
        max(abs(lc - luma(ul)), abs(lc - luma(ur))),
        max(abs(lc - luma(dl)), abs(lc - luma(dr)))
    );
    edge = max(edge, diagEdge * 0.70);

    // Mais força em letras/HUD/contornos; menos em áreas suaves para não granularizar fundos.
    mediump float edgeGate = smoothstep(0.025, 0.30, edge);
    mediump float amount = mix(0.10, 0.34, edgeGate);
    mediump vec3 sharpened = c + (c - localAvg) * amount;

    // Anti-ringing: nenhum canal pode criar pico fora da vizinhança imediata.
    mediump vec3 lo = min(c, min(min(l, r), min(u, d)));
    mediump vec3 hi = max(c, max(max(l, r), max(u, d)));
    lo = min(lo, min(min(ul, ur), min(dl, dr)));
    hi = max(hi, max(max(ul, ur), max(dl, dr)));
    sharpened = clamp(sharpened, lo, hi);

    // Microcontraste controlado para aumentar leitura do texto sem saturar sprites.
    mediump vec3 contrast = (sharpened - vec3(0.5)) * 1.025 + vec3(0.5);
    mediump vec3 finalColor = mix(sharpened, contrast, 0.55 * edgeGate);
    gl_FragColor = vec4(clamp(finalColor, 0.0, 1.0), 1.0);
}
)GLSL";

'''

if "const std::string donkeyMasterVertex" not in source:
    source = source.replace(marker, master_shader + marker, 1)

needle = '''                {
                    defines + cut3UpscalePass2Vertex,
                    defines + cut3UpscalePass2Fragment,
                    false,
                    1.0
                },
            },
            false
        };'''
replacement = '''                {
                    defines + cut3UpscalePass2Vertex,
                    defines + cut3UpscalePass2Fragment,
                    false,
                    1.0
                },
                {
                    donkeyMasterVertex,
                    donkeyMasterFragment,
                    false,
                    1.0
                },
            },
            false
        };'''

if replacement not in source:
    if needle not in source:
        raise SystemExit("Bloco CUT3 esperado não encontrado; abortando para não gerar build incorreta")
    source = source.replace(needle, replacement, 1)

CPP.write_text(source, encoding="utf-8")

# Alinhar o módulo local ao SDK do projeto principal.
gradle = GRADLE.read_text(encoding="utf-8")
gradle = gradle.replace('compileSdkVersion 33', 'compileSdkVersion 35')
gradle = gradle.replace('buildToolsVersion "34.0.0"', 'buildToolsVersion "35.0.0"')
gradle = gradle.replace('targetSdkVersion 31', 'targetSdkVersion 35')
GRADLE.write_text(gradle, encoding="utf-8")

# Verificações fail-fast.
final = CPP.read_text(encoding="utf-8")
assert "donkeyMasterFragment" in final
assert final.count("donkeyMasterVertex") >= 2
assert final.count("cut3UpscalePass2Fragment") >= 2
print("[OK] LibretroDroid custom: CUT3 + ScaleMaster adaptativo (4 passes)")
