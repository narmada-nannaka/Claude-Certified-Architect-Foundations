export async function getUser(req) {
  const id = req.params.id;
  const user = await db.query("SELECT * FROM users WHERE id = ?", [id]);
  return user;
}