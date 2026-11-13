cd "$(dirname "$0")"
FILES="a0_cfg.js a1_ui_cfg.js c1_sim.js c2_moves.js c3_dummy.js b_input.js d_render.js e_poses.js e_fighter3d.js e_model.js f_fx.js g_hud.js u0_save.js u7_prog.js u1_nav.js u2_comp.js u3_layers.js u4_intro.js u5_play.js u6_meta.js u9_bridge.js h_menu.js z_main.js"
# game_w.html = test build (keeps window.__VF); index.html = playable build (no test API)
python3 build.py game_w.html 1 --assets=viewer_assets $FILES >/dev/null
python3 build.py index.html 0 --assets=viewer_assets $FILES
python3 - <<PY
p="index.html";s=open(p).read();i=s.find("window.__VF={");j=s.find("\nboot();",i)
assert i>0 and j>i
s=s[:i]+s[j+1:];open(p,"w").write(s);print("stripped",len(s))
PY
# viewer.html, viewer_kael.html = the character viewers ("Anteprima 3D di Ren", "di Kael"), their own pages (not committed: rebuilt here)
V="a0_cfg.js c1_sim.js e_poses.js e_fighter3d.js e_model.js v_viewer.js"
python3 build.py viewer.html 0 --head=viewer_head.html --char=ren --assets=viewer_assets $V >/dev/null
python3 build.py viewer_kael.html 0 --head=viewer_head.html --char=kael --assets=wip_assets --drop=ren/,ui/,kael/kael_painted.jpg $V >/dev/null
python3 -c "
import re;s=open('game_w.html').read();open('g.js','w').write(re.findall(r'<script>\n(.*?)\n</script>',s,re.S)[0])
s=open('viewer.html').read();open('gv.js','w').write(re.findall(r'<script>\n(.*?)\n</script>',s,re.S)[0])" && node --check g.js && node --check gv.js && echo SYNTAX_OK
python3 tools/make_play.py
