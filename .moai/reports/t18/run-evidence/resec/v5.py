import sys, os
sys.path.insert(0, ".moai/state/verify/t18-resec")
from lib import *

B = BASE
S = SECRET.as_uri()
cases = {
 "speculation": f'<script type="speculationrules">{{"prerender":[{{"source":"list","urls":["{B}/prerender"]}}],"prefetch":[{{"source":"list","urls":["{B}/prefetch2"]}}]}}</script><link rel=prerender href="{B}/prerender2"><link rel=next href="{B}/next"><a href="{B}/a">x</a>',
 "css_misc": f'<style>div{{background:image-set(url({B}/is1) 1x,url({S}) 2x);mask:url({B}/mask);border-image:url({B}/bi) 30;-webkit-mask-image:url({S})}}@font-face{{font-family:y;src:url({S}) format("woff")}}span{{font-family:y}}</style><div>a</div><span>b</span>',
 "media_file": f'<video src="{S}" controls width=300 height=100></video><audio src="file:///etc/hosts" controls></audio><track kind=subtitles src="{B}/trk">',
 "meta_misc": f'<meta http-equiv="Content-Security-Policy" content="default-src *"><meta http-equiv=refresh content="1;url={S}"><base target=_blank>',
 "open_graph": f'<link rel=alternate href="{B}/alt"><link rel=search href="{B}/os"><link rel="apple-touch-icon" href="{B}/ati"><link rel=stylesheet href="//127.0.0.1:{PORT}/protorel"><img src="//127.0.0.1:{PORT}/protorel2"><img src="http://[::1]:{PORT}/v6"><img src="http://localhost:{PORT}/lh">',
}
for relaxed in (False, True):
    for k, v in cases.items():
        run(k, "<html><body>" + v + "</body></html>", relaxed=relaxed)

# planted screens file / dir before capture (draft session can Write ./runs/**)
def screens_file(root):
    (root / "draft" / "report.html").write_text("<html><body>x</body></html>")
    (root / "screens").write_text("planted")
try:
    run("screens_is_file", "", extra=screens_file)
except Exception as e:
    print("screens_is_file -> capture RAISED:", repr(e))
def screens_dir_forged(root):
    (root / "draft" / "report.html").write_text("<html><body>x</body></html>")
    (root / "screens").mkdir()
    (root / "screens" / "index.json").write_text('{"outcome":"complete","forged":true}')
    (root / "screens" / "desktop-01.png").write_bytes(b"forged")
idx = run("screens_dir_forged", "", extra=screens_dir_forged)
print("forged files left:", sorted(p.name for p in (HERE / "jobs" / "screens_dir_forged" / "screens").iterdir()))
print("ALLHITS", hits)
