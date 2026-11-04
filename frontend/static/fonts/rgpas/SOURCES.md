# RGPAS self-hosted fonts

Subsets of Noto Sans SC, Manrope and LXGW WenKai, distributed under SIL OFL 1.1.
The original licenses are included next to these WOFF2 files.

Regenerate: `python -m pip install "fonttools[woff]"` then `python frontend/tools/build_fonts.py`.
Source TTF files are cached locally and are not deployment assets.

UI subset covers the repository text; other characters use the declared system fallbacks.
Display subset covers current Chinese headings. Rebuild when adding headings.

## RGPAS Sans

- Upstream: https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf
- Source SHA-256: `a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da`
- Output: `ui-sans.woff2` (145,496 bytes)

## RGPAS Manrope

- Upstream: https://raw.githubusercontent.com/google/fonts/main/ofl/manrope/Manrope%5Bwght%5D.ttf
- Source SHA-256: `3ae11c49db0455a3cc33e37d380f20fdb8c7f8b41dc07625c177e3d87a9d6ae6`
- Output: `latin-sans.woff2` (29,340 bytes)

## RGPAS WenKai

- Upstream: https://raw.githubusercontent.com/lxgw/LxgwWenKai/main/fonts/TTF/LXGWWenKai-Medium.ttf
- Source SHA-256: `f4b8a34d1f838fe411540cb7c97b1c384ac9738a876c4104500bc42508b2312a`
- Output: `display-wenkai.woff2` (12,368 bytes)
