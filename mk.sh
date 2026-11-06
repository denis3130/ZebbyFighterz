cd "$(dirname "$0")"
FILES="a0_cfg.js z_main.js"
# game_w.html = test build (keeps window.__VF); index.html = playable build (no test API)
python3 build.py game_w.html 1 $FILES >/dev/null
python3 build.py index.html 0 $FILES
python3 - <<PY
p="index.html";s=open(p).read();i=s.find("window.__VF={");j=s.find("\nboot();",i)
assert i>0 and j>i
s=s[:i]+s[j+1:];open(p,"w").write(s);print("stripped",len(s))
PY
python3 -c "
import re;s=open('game_w.html').read();open('g.js','w').write(re.findall(r'<script>\n(.*?)\n</script>',s,re.S)[0])" && node --check g.js && echo SYNTAX_OK
