import * as fs from 'fs';

const store = '/etc/higoos-device-remarks';
const valid_key = /^[0-9a-f]{12}$/;

function reply(http, status, reason, data) {
	http.status(status, reason);
	http.header('Cache-Control', 'no-store');
	http.prepare_content('application/json');
	http.write_json(data);
}

function allowed(env) {
	return env.ctx?.authuser == 'root' && !!env.ctx?.authsession && !!env.ctx?.authtoken;
}

return {
	list: function(env) {
		const http = env.http, ctx = env.ctx;
		if (!allowed(env))
			return reply(http, 403, 'Forbidden', {});
		if (http.getenv('REQUEST_METHOD') != 'GET')
			return reply(http, 405, 'Method Not Allowed', {});
		const remarks = {};
		for (let key in fs.lsdir(store) ?? []) {
			if (!match(key, valid_key))
				continue;
			const note = fs.readfile(store + '/' + key, 257);
			if (type(note) == 'string' && length(note) <= 256)
				remarks[key] = note;
		}
		return reply(http, 200, 'OK', { remarks, token: ctx.authtoken });
	},
	save: function(env) {
		const http = env.http, ctx = env.ctx;
		if (!allowed(env) || http.getenv('REQUEST_METHOD') != 'POST' || http.formvalue('token') != ctx.authtoken)
			return reply(http, 403, 'Forbidden', {});
		const key = http.formvalue('mac');
		const raw = http.formvalue('note');
		if (type(key) != 'string' || !match(key, valid_key) ||
		    type(raw) != 'string' || length(raw) > 256 || match(raw, /[[:cntrl:]]/))
			return reply(http, 400, 'Bad Request', {});
		const note = trim(raw);
		const path = store + '/' + key;
		let ok;
		if (note == '') {
			ok = fs.unlink(path) || fs.lstat(path) == null;
		}
		else {
			fs.mkdir(store, 0700);
			// Atomically replace this MAC's file without affecting other devices.
			const random = fs.open('/dev/urandom', 'r');
			const bytes = random?.read(12);
			random?.close();
			const stage = bytes && length(bytes) == 12 ? store + '/.write.' + hexenc(bytes) : null;
			if (stage && fs.mkdir(stage, 0700)) {
				const draft = stage + '/note';
				ok = fs.writefile(draft, note) == length(note) && fs.rename(draft, path);
				if (!ok)
					fs.unlink(draft);
				fs.rmdir(stage);
			}
		}
		if (!ok)
			return reply(http, 500, 'Internal Server Error', {});
		return reply(http, 200, 'OK', { note });
	}
};
