<#
.SYNOPSIS
    Generates sample diff fixtures from real file modifications.

.DESCRIPTION
    For each fixture, creates a baseline file, commits it, then writes
    the modified version and captures the diff via git. Resets the
    file at the end. Validates each generated diff with `git apply --check`.

    This avoids the hand-written-diff failure mode where hunk headers
    don't match hunk body line counts.

.EXAMPLE
    .\scripts\generate_sample_diffs.ps1
#>
$ErrorActionPreference = "Stop"

# Locate the scenario root regardless of where we're invoked from
$ScenarioRoot = $PSScriptRoot | Split-Path -Parent
Set-Location $ScenarioRoot

Write-Host "Scenario root: $ScenarioRoot"

# Ensure required directories exist
New-Item -ItemType Directory -Path "src/api", "src/utils", "sample-diffs" -Force | Out-Null


function Generate-Diff {
    <#
    .SYNOPSIS
        Generates one sample diff by writing baseline + modified states.
    #>
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(Mandatory)][string]$Baseline,
        [Parameter(Mandatory)][string]$Modified,
        [Parameter(Mandatory)][string]$OutputDiff
    )

    Write-Host ""
    Write-Host "Generating $OutputDiff..."

    # Write and commit the baseline so git has something to diff against
    Set-Content -Path $FilePath -Value $Baseline -Encoding UTF8
    git add $FilePath 2>&1 | Out-Null
    git commit -m "fixture: baseline for $OutputDiff" 2>&1 | Out-Null

    # Write the modified version (entire content, not a transformation)
    Set-Content -Path $FilePath -Value $Modified -Encoding UTF8

    # Verify git actually sees a change. If not, the baseline and modified
    # are identical and we have a bug in our fixture definitions.
    $status = git status --porcelain $FilePath
    if (-not $status) {
        throw "No changes detected in $FilePath. Baseline and modified may be identical."
    }

    # Capture the diff via git itself (guaranteed valid hunk headers)
    $diff = git diff $FilePath
    if ([string]::IsNullOrWhiteSpace($diff)) {
        throw "git diff produced no output for $FilePath."
    }

    Set-Content -Path $OutputDiff -Value $diff -Encoding UTF8

    # Reset the working file
    git checkout $FilePath 2>&1 | Out-Null

    # Validate the generated diff applies cleanly
    git apply --no-index --check $OutputDiff 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "Generated diff $OutputDiff fails git apply --check"
    }

    Write-Host "  ✓ $OutputDiff valid"
}


# ============================================================================
# Fixture 1: good.diff — a SQL injection vulnerability
# A blocker-severity issue any review must catch
# ============================================================================

$goodBaseline = @'
export async function getUser(req) {
  const id = req.params.id;
  const user = await db.query("SELECT * FROM users WHERE id = ?", [id]);
  return user;
}
'@

$goodModified = @'
export async function getUser(req) {
  const id = req.params.id;
  const user = await db.query(`SELECT * FROM users WHERE id = '${id}'`);
  return user;
}
'@

Generate-Diff -FilePath "src/api/users.ts" `
    -Baseline $goodBaseline `
    -Modified $goodModified `
    -OutputDiff "sample-diffs/good.diff"


# ============================================================================
# Fixture 2: noisy.diff — adding a TODO comment
# Should produce zero findings (TODOs are acceptable per convention)
# ============================================================================

$noisyBaseline = @'
export function formatPrice(amount) {
  return `$${amount.toFixed(2)}`;
}
'@

$noisyModified = @'
export function formatPrice(amount) {
  return `$${amount.toFixed(2)}`;
}

// TODO: add support for other currencies
'@

Generate-Diff -FilePath "src/utils/format.ts" `
    -Baseline $noisyBaseline `
    -Modified $noisyModified `
    -OutputDiff "sample-diffs/noisy.diff"


# ============================================================================
# Fixture 3: mixed.diff — real issues + superficial concerns
# Tests calibration: flag real issues, ignore noise
# ============================================================================

$mixedBaseline = @'
import { OrderRepository } from "../repositories/OrderRepository";
import { logger } from "../utils/logger";

export async function processOrder(orderData) {
  logger.info("Processing order", { orderId: orderData.id });
  const repo = new OrderRepository();
  const result = await repo.save(orderData);
  return result;
}
'@

$mixedModified = @'
import { OrderRepository } from "../repositories/OrderRepository";
import { logger } from "../utils/logger";

export async function processOrder(orderData: any) {
  console.log("Processing order", { orderId: orderData.id });
  const repo = new OrderRepository();
  const result = await repo.save(orderData);
  // TODO: handle save errors
  return result;
}
'@

Generate-Diff -FilePath "src/api/orders.ts" `
    -Baseline $mixedBaseline `
    -Modified $mixedModified `
    -OutputDiff "sample-diffs/mixed.diff"


# ============================================================================
# Fixture 4: ambiguous.diff — edge cases for few-shot calibration (M5)
# Mix of a DEBUG-commented auth check (blocker) and an `any` at parse boundary
# ============================================================================

$ambiguousBaseline = @'
export async function authenticate(req) {
  const token = req.headers.authorization;
  const claims = parseJwt(token);
  return claims;
}
'@

$ambiguousModified = @'
export async function authenticate(req) {
  const token = req.headers.authorization;
  // DEBUG: temporarily skipping format validation
  const claims: any = parseJwt(token);
  return claims;
}
'@

Generate-Diff -FilePath "src/api/auth-handler.ts" `
    -Baseline $ambiguousBaseline `
    -Modified $ambiguousModified `
    -OutputDiff "sample-diffs/ambiguous.diff"


Write-Host ""
Write-Host "All four sample diffs generated and validated."
Write-Host ""
Write-Host "Generated diffs are in sample-diffs/:"
Get-ChildItem sample-diffs | Format-Table Name, Length