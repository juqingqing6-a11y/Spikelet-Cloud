"""Build self-hosted font subsets. Optional tooling: fonttools[woff] (not a server dependency)."""
import hashlib
import re
from pathlib import Path
from urllib.request import urlopen

from fontTools import subset
from fontTools.ttLib import TTFont

FRONTEND = Path(__file__).resolve().parents[1]
CACHE = FRONTEND.parent / '.cache' / 'frontend-fonts'
OUTPUT = FRONTEND / 'static' / 'fonts' / 'rgpas'
ROOT_URL = 'https://raw.githubusercontent.com/google/fonts/main/ofl/'
FONTS = (
    ('NotoSansSC', 'RGPAS Sans', 'ui-sans.woff2', 'ui',
     ROOT_URL + 'notosanssc/NotoSansSC%5Bwght%5D.ttf', ROOT_URL + 'notosanssc/OFL.txt'),
    ('Manrope', 'RGPAS Manrope', 'latin-sans.woff2', 'latin',
     ROOT_URL + 'manrope/Manrope%5Bwght%5D.ttf', ROOT_URL + 'manrope/OFL.txt'),
    ('LXGWWenKai-Medium', 'RGPAS WenKai', 'display-wenkai.woff2', 'display',
     'https://raw.githubusercontent.com/lxgw/LxgwWenKai/main/fonts/TTF/LXGWWenKai-Medium.ttf',
     'https://raw.githubusercontent.com/lxgw/LxgwWenKai/main/OFL.txt'),
)


def download(url, target):
    if not target.exists():
        with urlopen(url, timeout=60) as response:
            data = response.read()
        target.write_bytes(data)
    return target.read_bytes()


def build():
    CACHE.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    source = '\n'.join(path.read_text(encoding='utf-8') for path in
                       list((FRONTEND / 'templates').rglob('*.html')) +
                       list((FRONTEND / 'static' / 'js').glob('*analysis.js')) +
                       [FRONTEND / 'static' / 'css' / 'research-theme.css'])
    headings = re.findall(r'research_title_cn="([^"]+)"|<h[12][^>]*>([^<]+)', source)
    titles = '\n'.join(text for pair in headings for text in pair if text)
    # Brand headline is translated with literal newlines at runtime.
    titles += '\n从稻穗，到每一粒。穗粒表型分析系统注册账号采样手记完整入镜清晰成像有序归档'
    body_chars = {ord(char) for char in source if ord(char) >= 0x2e80}
    title_chars = {ord(char) for char in titles if ord(char) >= 0x2e80}
    latin_chars = set(range(0x20, 0x250)) | set(range(0x2000, 0x2070))
    provenance = ['# RGPAS self-hosted fonts', '',
                  'Subsets of Noto Sans SC, Manrope and LXGW WenKai, distributed under SIL OFL 1.1.',
                  'The original licenses are included next to these WOFF2 files.', '',
                  'Regenerate: `python -m pip install "fonttools[woff]"` then `python frontend/tools/build_fonts.py`.',
                  'Source TTF files are cached locally and are not deployment assets.', '',
                  'UI subset covers the repository text; other characters use the declared system fallbacks.',
                  'Display subset covers current Chinese headings. Rebuild when adding headings.', '']
    for upstream_name, family, filename, purpose, url, license_url in FONTS:
        raw = download(url, CACHE / (upstream_name + '.ttf'))
        license_data = download(license_url, CACHE / (upstream_name + '-OFL.txt'))
        (OUTPUT / (upstream_name + '-OFL.txt')).write_bytes(license_data)
        font = TTFont(CACHE / (upstream_name + '.ttf'), recalcTimestamp=False)
        options = subset.Options()
        options.name_IDs = ['*']
        options.name_legacy = True
        options.name_languages = ['*']
        options.layout_features = ['*']
        chars = {'display': title_chars, 'ui': body_chars, 'latin': latin_chars}[purpose]
        cmap = font.getBestCmap()
        requested = chars & set(cmap)
        worker = subset.Subsetter(options=options)
        worker.populate(unicodes=requested)
        worker.subset(font)
        for record in font['name'].names:
            if record.nameID in (1, 3, 4, 6, 16, 25):
                name = family.replace(' ', '-') if record.nameID in (3, 6, 25) else family
                record.string = name.encode(record.getEncoding())
        font.flavor = 'woff2'
        font.save(OUTPUT / filename)
        output_size = (OUTPUT / filename).stat().st_size
        print(f'{family}: {len(requested)} characters, {output_size:,} bytes', flush=True)
        provenance += [f'## {family}', '', f'- Upstream: {url}',
                       f'- Source SHA-256: `{hashlib.sha256(raw).hexdigest()}`',
                       f'- Output: `{filename}` ({output_size:,} bytes)', '']
    (OUTPUT / 'SOURCES.md').write_text('\n'.join(provenance), encoding='utf-8')


if __name__ == '__main__':
    build()
