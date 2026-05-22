$modified = @'
export async function getUser(req) {
  const id = req.params.id;
  const user = await db.query(`SELECT * FROM users WHERE id = '${id}'`);
  return user;
}
'@

Set-Content -Path "src/api/users.ts" -Value $modified -Encoding UTF8

# Verify the modification was applied
Get-Content "src/api/users.ts"