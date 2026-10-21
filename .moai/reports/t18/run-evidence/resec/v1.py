import sys
sys.path.insert(0, ".moai/state/verify/t18-resec")
from lib import *

B = BASE
S = SECRET.as_uri()
vec = {
 "iframe_file": f'<iframe src="{S}" width=700 height=100></iframe><iframe src="file:///etc/hosts" width=700 height=200></iframe>',
 "object_file": f'<object data="{S}" width=700 height=100></object><embed src="{S}" width=700 height=100>',
 "frameset": f'<frameset><frame src="{S}"><frame src="{B}/frame"></frameset>',
 "meta_refresh_file": f'<meta http-equiv=refresh content="0;url={S}">top',
 "meta_refresh_http": f'<meta http-equiv=refresh content="0;url={B}/mr">top',
 "meta_refresh_data": '<meta http-equiv=refresh content="0;url=data:text/html,<h1>DATAPAGE</h1>">top',
 "link_misc": f'<link rel=prefetch href="{B}/pf"><link rel=preload as=image href="{B}/pl"><link rel=stylesheet href="{S}"><link rel=icon href="{B}/icon"><link rel=manifest href="{B}/man"><link rel=modulepreload href="{B}/mp">',
 "css_urls": f'<style>@import url("{B}/imp"); @font-face{{font-family:x;src:url({B}/font)}} body{{font-family:x;background:url({B}/bg);list-style:url({B}/ls)}} p{{cursor:url({B}/cur),auto;content:url({B}/cnt)}}</style><p>css</p><style>@import url("{S}");</style>',
 "img_variants": f'<img srcset="{B}/s1 1x,{B}/s2 2x"><picture><source srcset="{B}/pic"><img src="{B}/pimg"></picture><video poster="{B}/poster" src="{B}/vid"></video><audio src="{B}/aud"></audio><img src="{S}"><input type=image src="{B}/inp">',
 "svg": f'<svg width=100 height=100><use href="{B}/x.svg#a"/><image href="{B}/svgimg"/><image href="{S}"/></svg><svg><foreignObject><iframe xmlns="http://www.w3.org/1999/xhtml" src="{B}/fo"></iframe></foreignObject></svg>',
 "form_ping": f'<form action="{B}/form" method=post id=f><input name=a value=1></form><a href="{B}/a" ping="{B}/ping" target=_blank id=l>link</a><button form=f formaction="{B}/fa">x</button><table background="{B}/tb"><tr><td>x</td></tr></table>',
 "srcdoc_nested": f'<iframe srcdoc="&lt;iframe src=&quot;{S}&quot;&gt;&lt;/iframe&gt;&lt;img src=&quot;{B}/sd&quot;&gt;"></iframe><iframe src="about:blank"></iframe><iframe src="javascript:document.write(1)"></iframe><iframe src="blob:http://x/y"></iframe><iframe src="filesystem:http://x/temporary/y"></iframe><iframe src="view-source:{S}"></iframe><iframe src="chrome://version"></iframe><iframe src="data:text/html,<h1>DATAFRAME</h1>"></iframe><iframe src="{B}/if"></iframe>',
 "base_tag": f'<base href="{B}/"><img src="rel.png"><a href="x">x</a>',
 "script_all": f'<script>fetch("{B}/fetch");new XMLHttpRequest().open("GET","{B}/xhr");new WebSocket("ws://127.0.0.1:{PORT}/ws");new EventSource("{B}/es");navigator.sendBeacon("{B}/beacon");window.open("{B}/wo");new Worker("{B}/w.js");navigator.serviceWorker&&navigator.serviceWorker.register("{B}/sw.js");document.body.innerHTML="SCRIPT-RAN";location="{B}/loc"</script><body>NOSCRIPT',
 "script_src": f'<script src="{B}/s.js"></script><script src="{S}"></script><script type=module src="{B}/m.js"></script>',
 "event_handlers": f'<img src=data:, onerror="fetch(\'{B}/onerror\');document.body.innerHTML=\'HANDLER-RAN\'"><body onload="fetch(\'{B}/onload\')">x',
 "js_url": f'<a href="javascript:fetch(\'{B}/jsurl\')" id=a>x</a><iframe src="javascript:fetch(\'{B}/jsif\')"></iframe>',
 "self_ref": '<iframe src="report.html"></iframe><link rel=stylesheet href="report.html">',
}
only = sys.argv[1:]
for relaxed in (False, True):
    for k, v in vec.items():
        if only and k not in only:
            continue
        if v.startswith("<frameset") or v.startswith("<script") or v.startswith("<meta"):
            h = "<html><head>" + v + "</head></html>" if v.startswith("<meta") else "<html>" + v + "</html>"
        else:
            h = "<html><body style='font-size:24px'>" + v + "</body></html>"
        run(k, h, relaxed=relaxed)
print("ALLHITS", hits)
