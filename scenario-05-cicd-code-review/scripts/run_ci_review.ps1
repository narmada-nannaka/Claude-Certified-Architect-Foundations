<#
.SYNOPSIS
    CI runner for Claude Code review (PowerShell port).

.DESCRIPTION
    Reviews a pull request diff using Claude Code in non-interactive
    mode and produces structured JSON findings.

    Per Task 3.6:
    - -p / --print runs Claude Code non-interactively (required for CI)
    - --output-format json produces machine-parseable output
    - --json-schema validates output against a schema file

.PARAMETER BaseSha
    The base commit SHA to diff against (typically the PR base branch HEAD).

.EXAMPLE
    .\scripts\run_ci_review.ps1 abc1234
#>
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$BaseSha
)

$ErrorActionPreference = "Stop"

# Configuration
$SchemaPath = ".claude/schemas/review-findings.json"
$OutputFile = "review-findings.json"

# Verify the schema file exists before running anything expensive
if (-not (Test-Path $SchemaPath)) {
    Write-Error "Schema file not found at $SchemaPath. Cannot run review."
    exit 2
}

# Compute the diff against the PR base
Write-Host "Computing diff from $BaseSha..HEAD..."
$Diff = git diff "$BaseSha..HEAD"

if ($LASTEXITCODE -ne 0) {
    Write-Error "git diff failed. Is $BaseSha a valid commit in this repo?"
    exit 2
}

if ([string]::IsNullOrWhiteSpace($Diff)) {
    Write-Host "No changes to review."
    '{"summary": "No changes.", "findings": []}' | Set-Content -Path $OutputFile -Encoding UTF8
    exit 0
}

# Build the prompt as a here-string for readability
$Prompt = @"
Review the following pull request diff against the team's review criteria
in .claude/CLAUDE.md and .claude/commands/review.md.

Produce structured findings via the submit_review_findings tool. Only flag
issues that meet the explicit criteria in the review command — do not flag
minor stylistic concerns.

DIFF:
``````diff
$Diff
``````
"@

# Run Claude Code non-interactively with structured output.
# We capture stdout and write it to the output file.
Write-Host "Invoking Claude Code review..."
$ClaudeOutput = claude -p $Prompt `
    --output-format json `
    --json-schema $SchemaPath

if ($LASTEXITCODE -ne 0) {
    Write-Error "Claude Code invocation failed with exit code $LASTEXITCODE"
    exit 3
}

# Persist the output
$ClaudeOutput | Set-Content -Path $OutputFile -Encoding UTF8
Write-Host "Review complete. Findings written to $OutputFile"

# Inspect findings for blocker severity
try {
    $Findings = $ClaudeOutput | ConvertFrom-Json
}
catch {
    Write-Error "Claude's output could not be parsed as JSON. Schema enforcement may have failed."
    exit 3
}

$Blockers = @($Findings.findings | Where-Object { $_.severity -eq "blocker" })

if ($Blockers.Count -gt 0) {
    Write-Host ""
    Write-Host "BLOCKER-severity findings present ($($Blockers.Count)). Failing the build."
    foreach ($b in $Blockers) {
        Write-Host "  - $($b.location.file):$($b.location.line) - $($b.issue)"
    }
    exit 1
}

Write-Host "No blocker findings. Review passed."
exit 0