#!/usr/bin/env python3
"""Add bounded-concurrency latency tests to the HigoOS OpenClash runtime tab."""
from pathlib import Path
import sys


HANDLER = '''const h5000mBulkTesting=g(!1),h5000mBulkProgress=g("");async function h5000mRunAllLatency(){if(t.value||j.value||c.value||w.value||!v.value?.coreAvailable||h5000mBulkTesting.value)return;const h5000mNodes=Object.entries(H.value).filter(([,entry])=>!Array.isArray(entry.all)).map(([name])=>name);if(!h5000mNodes.length){V.value="没有可测速的代理";return}h5000mBulkTesting.value=!0;t.value=!0;let h5000mNext=0,h5000mDone=0,h5000mFailed=0;h5000mBulkProgress.value=`0/${h5000mNodes.length}`;V.value="正在批量测速";const h5000mWorker=async()=>{while(h5000mNext<h5000mNodes.length){const name=h5000mNodes[h5000mNext++];try{const task=await $.action("test-latency",name);let finished=!1;for(let attempt=0;attempt<90;attempt++){const job=await $.job(task.jobId);if(job.state==="failed")throw new Error(job.error||"测速失败");if(job.state==="succeeded"){const result=job.result;if(result&&typeof result==="object"&&"delayMs"in result&&"name"in result)de.value[String(result.name)]=Number(result.delayMs);finished=!0;break}await new Promise(resolve=>setTimeout(resolve,1e3))}if(!finished)throw new Error("测速任务超时")}catch{h5000mFailed++}h5000mDone++;h5000mBulkProgress.value=`${h5000mDone}/${h5000mNodes.length}`}};try{await Promise.all(Array.from({length:Math.min(5,h5000mNodes.length)},()=>h5000mWorker()));const summary=`批量测速完成：成功 ${h5000mDone-h5000mFailed}，失败 ${h5000mFailed}`;await N();V.value=summary}catch(error){U(error)}finally{t.value=!1;h5000mBulkTesting.value=!1}};'''

ROW = '''s("div",{class:"mb-3 flex items-center justify-between gap-3"},[s("span",{class:"text-sm"},n(h5000mBulkTesting.value?`测速进度 ${h5000mBulkProgress.value}`:`共 ${Re.value.length} 个代理`),1),m(i(p),{variant:"secondary",disabled:t.value||j.value||!v.value?.coreAvailable||h5000mBulkTesting.value,onClick:h5000mRunAllLatency},{default:r(()=>[d(h5000mBulkTesting.value?"正在测速…":"一键测速",1)]),_:1},8,["disabled"])]),'''


def patch(root: Path) -> str:
    assets = root / "usr/share/higoros/web/assets"
    pages = sorted(assets.glob("OpenClashPage-*.js"))
    if len(pages) != 1:
        raise SystemExit(f"ERROR: expected one OpenClashPage asset, found {len(pages)}")
    page = pages[0]
    source = page.read_text(encoding="utf-8")

    if "h5000mRunAllLatency" in source:
        if source.count("h5000mRunAllLatency") != 2 or source.count("一键测速") != 1:
            raise SystemExit("ERROR: partial or duplicate bulk-latency patch detected")
        return "PASS: OpenClash runtime page already has the one-click latency test"

    handler_anchor = "async function T(a,e,l,u){"
    runtime_anchor = 'f.value==="runtime"?(o(),y("section",Fl,['
    proxy_list_anchor = '(o(!0),y(E,null,O(Be.value,'
    if source.count(handler_anchor) != 1:
        raise SystemExit(f"ERROR: expected one runtime action handler, found {source.count(handler_anchor)}")
    if source.count(runtime_anchor) != 1 or source.count(proxy_list_anchor) != 1:
        raise SystemExit("ERROR: OpenClash runtime tab render anchors changed")

    source = source.replace(handler_anchor, HANDLER + handler_anchor, 1)
    source = source.replace(runtime_anchor, runtime_anchor + ROW, 1)
    if source.count("h5000mRunAllLatency") != 2 or source.count("一键测速") != 1:
        raise SystemExit("ERROR: one-click latency handler and control were not both emitted")
    page.write_text(source, encoding="utf-8")
    return "PASS: added a bounded-concurrency one-click latency test to the OpenClash runtime tab"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch-higoros-openclash-bulk-latency.py ROOTFS_DIR")
    print(patch(Path(sys.argv[1])))
