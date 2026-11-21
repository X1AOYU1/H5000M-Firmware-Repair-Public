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
replacement = '''setup(a){const s=at(),e=ta();let h5000mSaved=5;try{h5000mSaved=Number(localStorage.getItem("h5000m-dashboard-refresh"))||5}catch{}const h5000mInterval=M([2,3,5].includes(h5000mSaved)?h5000mSaved:5);let h5000mTimer=null,h5000mPending=!1,h5000mActive=!0;const h5000mSchedule=()=>{clearTimeout(h5000mTimer);h5000mTimer=setTimeout(async()=>{if(!document.hidden&&!h5000mPending&&!e.isRefreshing.value){h5000mPending=!0;try{await e.refresh()}catch{}finally{h5000mPending=!1}}h5000mActive&&h5000mSchedule()},h5000mInterval.value*1000)};const h5000mChange=w=>{h5000mInterval.value=Number(w.target.value);try{localStorage.setItem("h5000m-dashboard-refresh",String(h5000mInterval.value))}catch{}h5000mSchedule()};je(h5000mSchedule);Te(()=>{h5000mActive=!1;clearTimeout(h5000mTimer)});const n=p(()=>Re(e.trafficPeriod.value)?0:10)'''
ui = 't("div",vo,[t("button",{class:"btn-primary flex items-center gap-2"'
ui_new = 't("div",vo,[t("label",{class:"flex items-center gap-2 text-sm text-txt-2"},[t("span",null,"刷新间隔"),t("select",{value:h5000mInterval.value,onChange:h5000mChange,class:"rounded-lg border border-line-1 bg-bg-1 px-2 py-2 text-txt-1","aria-label":"仪表板刷新间隔"},[t("option",{value:2},"2秒"),t("option",{value:3},"3秒"),t("option",{value:5},"5秒")],40,["value"])]),t("button",{class:"btn-primary flex items-center gap-2"'
if body.count(anchor) != 1 or body.count(ui) != 1:
    raise SystemExit('ERROR: dashboard refresh anchors changed')
body = body.replace(anchor, replacement, 1).replace(ui, ui_new, 1)
page.write_text(body, encoding='utf-8')
print('Dashboard refresh control installed')
