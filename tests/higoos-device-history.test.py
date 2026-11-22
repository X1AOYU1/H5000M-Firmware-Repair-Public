"""Run the packed history handler with authenticated requests and failing IO."""
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path(sys.argv[1])
source = (root / 'usr/lib/lua/luci/controller/openclash.lua').read_text(encoding='utf-8')
assert source.count('"device_history"}, call("action_higoros_device_history")') == 1
start = source.index('function action_higoros_device_history()')
handler = source[start:source.index('\nfunction action_backup()', start)]
test = r'''
local context={authuser="root",authsession="session",authtoken="csrf"}
local files,request,fail,headers={},nil,nil,{}
local store="/etc/higoos-forgotten-devices"
local key="0af1b0c04019"
package.preload["luci.dispatcher"]=function()return {context=context}end
package.preload["luci.http"]=function()return {
 status=function(code)request.status=code end,prepare_content=function()end,header=function(k,v)headers[k]=v end,
 getenv=function(k)if k=="REQUEST_METHOD"then return request.method end if k=="HTTP_ORIGIN"then return request.origin end if k=="HTTP_HOST"then return request.host end end,
 formvalue=function(k)return request[k]end,
 write_json=function(data)request.data=data end
}end
package.preload["nixio.fs"]=function()return {
 dir=function()local keys={} for path in pairs(files)do
  if path:sub(1,#store+1)==store.."/" then keys[#keys+1]=path:sub(#store+2)end end
  local i=0;return function()i=i+1;return keys[i]end end,
 readfile=function(path)if path=="/proc/sys/kernel/random/uuid" then return "1234-abcd\n" end return files[path]end,
 mkdirr=function()return fail~="mkdir" end, stat=function()return nil end,chmod=function()return true end,
 writefile=function(path,value)if fail=="write"then return nil end files[path]=value;return #value end,
 rename=function(a,b)if fail=="rename"then return nil end files[b]=files[a];files[a]=nil;return true end,
 unlink=function(path)if fail=="unlink"then return nil end files[path]=nil;return true end
}end
'''+handler+r'''
local function run(method,action,mac,token,generation)
 request={method=method,action=action,mac=mac,token=token,generation=generation,status=200,origin="http://router",host="router:8080"}
 headers={}
 action_higoros_device_history();return request.status,request.data
end
local status,data=run("GET")
assert(status==200 and data.token=="csrf" and next(data.markers)==nil)
assert(headers["Access-Control-Allow-Origin"]=="http://router" and headers["Access-Control-Allow-Credentials"]=="true")
assert(headers["Access-Control-Allow-Methods"]=="GET, POST, OPTIONS")
assert(run("OPTIONS")==200)
context.authuser="guest";assert(run("GET")==403);context.authuser="root"
assert(run("DELETE")==405)
assert(run("POST","forget",key,"wrong")==403)
assert(run("POST","forget","../../passwd","csrf")==400)
assert(run("POST","block",key,"csrf")==400)
for _,fault in ipairs({"mkdir","write","rename"})do
 fail=fault;assert(run("POST","forget",key,"csrf")==500)
 assert(files[store.."/"..key]==nil)
end
fail=nil;status,data=run("POST","forget",key,"csrf")
assert(status==200 and data.generation=="1234-abcd")
local _,loaded=run("GET");assert(loaded.markers[key]==data.generation)
assert(run("POST","restore",key,"csrf","old")==409)
fail="unlink";assert(run("POST","restore",key,"csrf",data.generation)==500)
fail=nil;assert(run("POST","restore",key,"csrf",data.generation)==200)
assert(files[store.."/"..key]==nil)
assert(run("POST","restore",key,"csrf",data.generation)==200)
print("PASS: packed history auth, CSRF, traversal rejection, persistence, IO errors and generation-safe reconnect")
'''
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / 'history.lua'
    path.write_text(test, encoding='utf-8')
    subprocess.run(['lua5.1', str(path)], check=True)
