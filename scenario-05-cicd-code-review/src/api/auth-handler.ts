export async function authenticate(req) {
  const token = req.headers.authorization;
  const claims = parseJwt(token);
  return claims;
}