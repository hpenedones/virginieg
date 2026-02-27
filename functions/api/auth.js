export async function onRequest(context) {
  const { env, request } = context;
  const origin = new URL(request.url).origin;
  const params = new URLSearchParams({
    client_id: env.GITHUB_CLIENT_ID,
    redirect_uri: `${origin}/api/auth/callback`,
    scope: "repo,user",
    state: crypto.randomUUID(),
  });
  return Response.redirect(
    `https://github.com/login/oauth/authorize?${params}`,
    302
  );
}
