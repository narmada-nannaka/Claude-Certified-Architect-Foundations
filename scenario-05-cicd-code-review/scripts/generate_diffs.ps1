# Make sure the directory exists
New-Item -ItemType Directory -Path "src/api" -Force | Out-Null

# Write the baseline using a here-string (no escape ambiguity)
$baseline = @'
export async function getUser(req) {
  const id = req.params.id;
  const user = await db.query("SELECT * FROM users WHERE id = ?", [id]);
  return user;
}
'@

Set-Content -Path "src/api/users.ts" -Value $baseline -Encoding UTF8

# Verify what we wrote
Get-Content "src/api/users.ts"