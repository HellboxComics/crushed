// THE PAGE IS THE MACHINE (Cody, 2026-10-05): the phone page's inputs land here and the Mac picks them up.
// A Cloudflare Pages Function (developers.cloudflare.com/pages/functions/get-started/ - file-based routing,
// onRequest handlers, context.env bindings) with one KV store bound as INBOX
// (developers.cloudflare.com/pages/functions/bindings/#kv-namespaces, wrangler.toml [[kv_namespaces]]).
//   POST /api/act    {token, action, item?, text?, photo?}   -> one message in the box (7-day life)
//   GET  /api/inbox?token=..                                  -> every message waiting (the Mac, once a minute)
//   POST /api/ack    {token, keys:[..]}                        -> the Mac says it has them; they are removed
//   GET  /api/ping                                             -> {ok, waiting}
// The token is the one line in the KV key "_token" (the Mac puts it there at setup); nothing happens without it.
const ACTIONS = new Set(["add", "note", "keep", "redo", "retry", "restart", "job_on", "job_off", "pick", "size"]);

const json = (obj, status = 200) => new Response(JSON.stringify(obj), {
  status, headers: { "content-type": "application/json", "cache-control": "no-store" } });

async function allowed(env, token) {
  if (!env.INBOX) return false;
  const want = await env.INBOX.get("_token");
  return Boolean(want) && Boolean(token) && token === want;
}

export async function onRequest(context) {
  const { request, env, params } = context;
  const route = (params.route || []).join("/");
  const url = new URL(request.url);
  if (route === "ping" && request.method === "GET") {
    const list = env.INBOX ? await env.INBOX.list({ prefix: "in:" }) : { keys: [] };
    return json({ ok: true, waiting: list.keys.length, bound: Boolean(env.INBOX) });
  }
  if (route === "act" && request.method === "POST") {
    let body;
    try { body = await request.json(); } catch (e) { return json({ ok: false, why: "not JSON" }, 400); }
    if (!(await allowed(env, body.token))) return json({ ok: false, why: "wrong token" }, 403);
    if (!ACTIONS.has(body.action)) return json({ ok: false, why: "unknown action" }, 400);
    if (body.photo && typeof body.photo === "string" && body.photo.length > 20 * 1024 * 1024)
      return json({ ok: false, why: "photo too big (20 MB)" }, 413);
    const key = "in:" + Date.now() + ":" + Math.random().toString(36).slice(2, 8);
    const msg = { key, at: Date.now(), action: body.action, item: body.item || null, text: body.text || "",
                  photo: body.photo || null, from: request.headers.get("cf-connecting-ip") || "" };
    await env.INBOX.put(key, JSON.stringify(msg), { expirationTtl: 7 * 24 * 3600 });
    return json({ ok: true, key });
  }
  if (route === "inbox" && request.method === "GET") {
    if (!(await allowed(env, url.searchParams.get("token")))) return json({ ok: false, why: "wrong token" }, 403);
    const list = await env.INBOX.list({ prefix: "in:" });
    const out = [];
    for (const k of list.keys) {
      const v = await env.INBOX.get(k.name);
      if (v) { try { out.push(JSON.parse(v)); } catch (e) { out.push({ key: k.name, broken: true }); } }
    }
    out.sort((a, b) => (a.at || 0) - (b.at || 0));
    return json({ ok: true, messages: out });
  }
  if (route === "ack" && request.method === "POST") {
    let body;
    try { body = await request.json(); } catch (e) { return json({ ok: false, why: "not JSON" }, 400); }
    if (!(await allowed(env, body.token))) return json({ ok: false, why: "wrong token" }, 403);
    for (const k of body.keys || []) if (typeof k === "string" && k.startsWith("in:")) await env.INBOX.delete(k);
    return json({ ok: true, removed: (body.keys || []).length });
  }
  return json({ ok: false, why: "no such door" }, 404);
}
