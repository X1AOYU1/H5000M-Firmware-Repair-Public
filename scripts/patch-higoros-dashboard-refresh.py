#!/usr/bin/env python3
from pathlib import Path
import sys

root = Path(sys.argv[1])
assets = root / 'usr/share/higoros/web/assets'
pages = list(assets.glob('DashboardPage-*.js'))
if len(pages) != 1:
    raise SystemExit('ERROR: expected one dashboard asset')
page = pages[0]
body = page.read_text(encoding='utf-8')
anchor = 'setup(a){const s=at(),e=ta(),n=p(()=>Re(e.trafficPeriod.value)?0:10)'
replacement = '''setup(a){const s=at(),e=ta();let h5000mSaved=5;try{h5000mSaved=Number(localStorage.getItem("h5000m-dashboard-refresh"))||5}catch{}const h5000mInterval=M([1,2,3,5].includes(h5000mSaved)?h5000mSaved:5);let h5000mTimer=null;const h5000mTick=()=>{if(!document.hidden)e.refresh().catch(()=>{})};const h5000mSchedule=()=>{clearInterval(h5000mTimer);h5000mTimer=setInterval(h5000mTick,h5000mInterval.value*1000)};const h5000mChange=w=>{const value=Number(w.target.value);if(![1,2,3,5].includes(value))return;h5000mInterval.value=value;try{localStorage.setItem("h5000m-dashboard-refresh",String(value))}catch{}h5000mSchedule();h5000mTick()};const h5000mVisible=()=>{if(!document.hidden){h5000mSchedule();h5000mTick()}};je(()=>{h5000mSchedule();document.addEventListener("visibilitychange",h5000mVisible)});Te(()=>{clearInterval(h5000mTimer);document.removeEventListener("visibilitychange",h5000mVisible)});const n=p(()=>Re(e.trafficPeriod.value)?0:10)'''
ui = 't("div",vo,[t("button",{class:"btn-primary flex items-center gap-2"'
ui_new = 't("div",vo,[t("label",{class:"flex items-center gap-2 text-sm text-txt-2"},[t("span",null,"刷新间隔"),t("select",{value:h5000mInterval.value,onChange:h5000mChange,class:"rounded-lg border border-line-1 bg-bg-1 px-2 py-2 text-txt-1","aria-label":"仪表板刷新间隔"},[t("option",{value:1},"实时"),t("option",{value:2},"2秒"),t("option",{value:3},"3秒"),t("option",{value:5},"5秒")],40,["value"])]),t("button",{class:"btn-primary flex items-center gap-2"'
if body.count(anchor) != 1 or body.count(ui) != 1:
    raise SystemExit('ERROR: dashboard refresh anchors changed')
body = body.replace(anchor, replacement, 1).replace(ui, ui_new, 1)
# The dashboard owns one clock. A slow optional query must not block the
# traffic/device queries, nor may it be cancelled and restarted every tick.
edits = [
    ('he=5e3,et=3e4,', 'he=!1,et=!1,'),
    ('s=lt(!0),e=ut(),n=pt(),i=dt("",{refetchInterval:5e3})',
     's=lt(!1),e=ut({refetchInterval:!1}),n=pt(),i=dt("",{refetchInterval:!1})'),
    ('await Promise.allSettled(ie.map(g=>g.refetch()))',
     'await Promise.allSettled(ie.filter(g=>!g.isFetching.value&&(g!==C||L.value)).map(g=>g.refetch({cancelRefetch:!1})))'),
]
for old, new in edits:
    if body.count(old) != 1:
        raise SystemExit('ERROR: dashboard query anchor changed: ' + old)
    body = body.replace(old, new, 1)

# Allow this page to disable the WiFi settings query's startup polling without
# altering the default behaviour of wireless settings and other pages.
wireless = list(assets.glob('wireless.commands-*.js'))
if len(wireless) != 1:
    raise SystemExit('ERROR: expected one wireless query asset')
wifi = wireless[0].read_text(encoding='utf-8')
start = 'Ie=()=>p({queryKey:o.settings()'
end = '?!1:te}}),Me='
if wifi.count(start) != 1 or wifi.count(end) != 1:
    raise SystemExit('ERROR: wireless settings polling anchors changed')
wifi = wifi.replace(start, 'Ie=(h5000mOptions={})=>p({queryKey:o.settings()', 1)
wifi = wifi.replace(end, '?!1:te},...h5000mOptions}),Me=', 1)
wireless[0].write_text(wifi, encoding='utf-8')
page.write_text(body, encoding='utf-8')
print('Dashboard refresh control installed')
