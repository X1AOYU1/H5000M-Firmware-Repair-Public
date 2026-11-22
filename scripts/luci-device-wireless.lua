function action_higoros_device_wireless()
	local HTTP = require "luci.http"
	local context = require("luci.dispatcher").context or {}
	HTTP.prepare_content("application/json")
	if context.authuser ~= "root" or not context.authsession then
		HTTP.status(403, "Forbidden")
		return HTTP.write_json({ error = "请重新登录" })
	end
	if HTTP.getenv("REQUEST_METHOD") ~= "GET" then
		HTTP.status(405, "Method Not Allowed")
		return HTTP.write_json({ error = "请求方法不支持" })
	end
	HTTP.header("Cache-Control", "no-store")
	local result = { interfaces = {}, complete = false }
	-- Lua ubus timeouts are seconds, not milliseconds.
	local ok, bus = pcall(function() return require("ubus").connect(nil, 1) end)
	if not ok or not bus then return HTTP.write_json(result) end
	local deadline = os.time() + 2
	local function call(object, method, args)
		if os.time() >= deadline then return nil end
		local success, data = pcall(bus.call, bus, object, method, args or {})
		return success and type(data) == "table" and data or nil
	end
	local function band(frequency)
		local f = tonumber(frequency) or 0
		if f >= 2400 and f < 2500 then return "wifi-2.4g" end
		if f >= 4900 and f < 5925 then return "wifi-5g" end
		if f >= 5925 and f <= 7125 then return "wifi-6g" end
	end
	local function mac(value)
		return type(value) == "string" and value:match("^%x%x:%x%x:%x%x:%x%x:%x%x:%x%x$") and value:lower() or nil
	end
	local status = call("network.wireless", "status")
	local uci_ok, uci = pcall(function() return require("uci").cursor() end)
	local expected, total = {}, 0
	-- Runtime interface names are essential: never infer a band from ra/phy
	-- numbering, SSID text, or the number of radios in the product.
	for radio, data in pairs(status or {}) do
		if type(data) == "table" and data.up == true then
			for _, iface in ipairs(data.interfaces or {}) do
				local config = iface.config or {}
				if type(iface.ifname) == "string" and config.mode == "ap" then
					local configured = uci_ok and uci:get("wireless", radio, "band") or nil
					expected[iface.ifname] = ({["2g"]="wifi-2.4g",["5g"]="wifi-5g",["6g"]="wifi-6g"})[configured]
						or band(config.frequency) or ""
					total = total + 1
				end
			end
		end
	end
	local objects_ok, objects = pcall(bus.objects, bus)
	if objects_ok then
		for _, object in ipairs(objects or {}) do
			local iface = object:match("^hostapd%.(.+)$")
			if iface and expected[iface] == nil then expected[iface] = ""; total = total + 1 end
		end
	end
	local successful = 0
	for iface, configured_band in pairs(expected) do
		local clients = call("hostapd." .. iface, "get_clients")
		local row = { iface = iface, band = configured_band, clients = {} }
		local valid = clients and type(clients.clients) == "table"
		if valid then
			row.band = band(clients.freq) or row.band
			for address, station in pairs(clients.clients) do
				local key = mac(address)
				if key and type(station) == "table" and station.assoc == true then
					row.clients[#row.clients + 1] = { mac = key, signalDbm = tonumber(station.signal) }
				end
			end
		else
			local info = call("iwinfo", "info", {device=iface})
			local list = call("iwinfo", "assoclist", {device=iface})
			valid = info and info.mode == "Master" and list and type(list.results) == "table"
			if valid then
				row.band = band(info.frequency) or row.band
				for _, station in ipairs(list.results) do
					local key = mac(station.mac)
					if key then row.clients[#row.clients + 1] = {mac=key, signalDbm=tonumber(station.signal)} end
				end
			end
		end
		if valid then
			successful = successful + 1
			result.interfaces[#result.interfaces + 1] = row
		end
	end
	result.complete = status ~= nil and objects_ok and total > 0 and successful == total
	bus:close()
	if uci_ok then uci:unload("wireless") end
	return HTTP.write_json(result)
end
