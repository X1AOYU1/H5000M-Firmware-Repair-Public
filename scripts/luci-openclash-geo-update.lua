function action_h5000m_geo_update()
	local kind = HTTP.formvalue("kind")
	local updaters = {
		ipdb = "openclash_geo.sh ipdb",
		geoip = "openclash_geo.sh geoip",
		geosite = "openclash_geo.sh geosite",
		geoasn = "openclash_geo.sh geoasn",
		chnroute = "openclash_chnroute.sh"
	}
	local updater = updaters[kind or ""]
	HTTP.prepare_content("application/json")
	if not updater then
		HTTP.status(400, "Bad Request")
		return HTTP.write_json({ status = "error" })
	end
	if SYS.call("/usr/share/openclash/" .. updater .. " </dev/null >/dev/null 2>&1 &") ~= 0 then
		HTTP.status(503, "Service Unavailable")
		return HTTP.write_json({ status = "error" })
	end
	return HTTP.write_json({ status = "queued", kind = kind })
end
