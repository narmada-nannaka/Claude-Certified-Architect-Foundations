import crypto from "node:crypto";

export function hashPassword(password: string): string {
  // Implementation placeholder
  return crypto.createHash("sha256").update(password).digest("hex");
}

export function generateToken(): string {
  return crypto.randomBytes(32).toString("hex");
}