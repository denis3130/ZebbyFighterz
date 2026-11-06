import sys, os, json, base64
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'src')
ASSET_DIR = os.path.join(ROOT, 'assets')
MIME = {'.jpg': 'image/jpeg', '.png': 'image/png'}

def assets():
    """{path relative to assets/: data URI} for every jpg/png under assets/ (empty if there is no folder)."""
    out = {}
    for d, _, names in os.walk(ASSET_DIR):
        for n in sorted(names):
            ext = os.path.splitext(n)[1].lower()
            if ext in MIME:
                p = os.path.join(d, n)
                key = os.path.relpath(p, ASSET_DIR).replace(os.sep, '/')
                out[key] = 'data:%s;base64,%s' % (MIME[ext], base64.b64encode(open(p, 'rb').read()).decode())
    return dict(sorted(out.items()))

def build(out, js, wrap=False):
    head = open(os.path.join(SRC, 'head.html'), encoding='utf-8').read()
    code = '\n'.join(open(os.path.join(SRC, f), encoding='utf-8').read() for f in js)
    a = 'const ASSETS=' + json.dumps(assets(), separators=(',', ':')) + ';\n'
    html = head + '\n<script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>\n<script>\n(()=>{\n' + a + code + '\n})();\n</script>\n'
    if wrap:
        html = '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px/1.4 system-ui,sans-serif}img{max-width:100%}[hidden]{display:none!important}</style></head><body>' + html + '</body></html>'
    open(out, 'w', encoding='utf-8').write(html)
    return len(html)

if __name__ == '__main__':
    out = sys.argv[1]; wrap = sys.argv[2] == '1'; js = sys.argv[3:]
    print(build(out, js, wrap))
