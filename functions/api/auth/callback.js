export async function onRequest(context) {
  const { env, request } = context;
  const { searchParams } = new URL(request.url);
  const code = searchParams.get("code");

  const tokenRes = await fetch("https://github.com/login/oauth/access_token", {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify({
      client_id: env.GITHUB_CLIENT_ID,
      client_secret: env.GITHUB_CLIENT_SECRET,
      code,
    }),
  });
  const { access_token, error } = await tokenRes.json();

  if (error || !access_token) {
    return new Response(`OAuth error: ${error}`, { status: 400 });
  }

  const payload = JSON.stringify({ token: access_token, provider: "github" });
  const html = `<!DOCTYPE html><html><body><script>
    (function() {
      function cb(e) {
        window.opener.postMessage(
          "authorization:github:success:${payload.replace(/"/g, '\\"')}",
          e.origin
        );
      }
      window.addEventListener("message", cb, false);
      window.opener.postMessage("authorizing:github", "*");
    })();
  </script></body></html>`;

  return new Response(html, { headers: { "Content-Type": "text/html" } });
}
