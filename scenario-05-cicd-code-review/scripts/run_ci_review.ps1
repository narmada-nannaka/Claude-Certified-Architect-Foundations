<#
.SYNOPSIS
    CI runner for Claude Code review.

.DESCRIPTION
    Runs Claude Code non-interactively (-p flag) against a PR diff and
    produces structured JSON findings.

    Per Task 3.6:
    - -p / --print runs Claude Code non-interactively
    - --output-format json produces machine-parseable output
    - --json-schema validates output against the schema

.PARAMETER BaseSha
    The base commit SHA to diff against.

.EXAMPLE
    .\scripts\run_ci_review.ps1 HEAD
#>
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$BaseSha
)

$ErrorActionPreference = "Stop"

$SchemaPath = ".claude/schemas/review-findings.json"
$OutputFile = "review-findings.json"

if (-not (Test-Path $SchemaPath)) {
    Write-Error "Schema file not found at $SchemaPath."
    exit 2
}

Write-Host "Computing diff from $BaseSha..."

# git diff returns a string array (one per line); join into a single string
$DiffLines = git diff "$BaseSha..HEAD"
$Diff = if ($DiffLines) { $DiffLines -join "`n" } else { "" }

if ([string]::IsNullOrWhiteSpace($Diff)) {
    Write-Host "No committed changes vs $BaseSha. Checking working tree..."
    $DiffLines = git diff $BaseSha
    $Diff = if ($DiffLines) { $DiffLines -join "`n" } else { "" }
}

# Debug visibility (remove later)
Write-Host "Diff length captured: $($Diff.Length) characters"

if ([string]::IsNullOrWhiteSpace($Diff)) {
    Write-Host "No changes to review."
    '{"summary": "No changes.", "findings": []}' | Set-Content -Path $OutputFile -Encoding UTF8
    exit 0
}

$Prompt = @"
Review the following pull request diff against the team's review
criteria in .claude/CLAUDE.md and .claude/commands/review.md.

Produce structured JSON findings matching .claude/schemas/review-findings.json.
Only flag issues that meet the explicit criteria — do not flag minor
stylistic concerns.

DIFF:
``````diff
`$Diff
``````
"@

# Write the prompt to a temporary file to avoid PowerShell's
# argument-splitting quirks with multi-line strings passed to
# external commands.
$PromptFile = [System.IO.Path]::GetTempFileName()
try {
    [System.IO.File]::WriteAllText(
        $PromptFile,
        $Prompt,
        (New-Object System.Text.UTF8Encoding $false)
    )

    Write-Host "Invoking Claude Code review..."
    Write-Host "Calling claude..."
    $ClaudeOutput = claude -p $PromptContent `
        --output-format json `
        --json-schema $SchemaPath

    Write-Host ""
    Write-Host "=== ClaudeOutput type: $($ClaudeOutput.GetType().Name) ==="
    if ($ClaudeOutput -is [array]) {
        Write-Host "ClaudeOutput is an array with $($ClaudeOutput.Count) elements"
        Write-Host "First 500 chars of joined output:"
        $joined = $ClaudeOutput -join "`n"
        Write-Host $joined.Substring(0, [Math]::Min(500, $joined.Length))
        Write-Host "..."
        # Re-join into a single string for downstream processing
        $ClaudeOutput = $joined
    } else {
        Write-Host "ClaudeOutput is a single string of $($ClaudeOutput.Length) chars"
        Write-Host "First 500 chars:"
        Write-Host $ClaudeOutput.Substring(0, [Math]::Min(500, $ClaudeOutput.Length))
    }
    Write-Host "=== End ClaudeOutput debug ==="
    Write-Host ""
}
finally {
    # Clean up the temp file even if claude errors out
    if (Test-Path $PromptFile) {
        Remove-Item $PromptFile -Force
    }
}

if ($LASTEXITCODE -ne 0) {
    Write-Error "Claude Code invocation failed with exit code $LASTEXITCODE"
    exit 3
}

$ClaudeOutput | Set-Content -Path $OutputFile -Encoding UTF8
Write-Host "Review complete. Findings written to $OutputFile"

try {
    $Findings = $ClaudeOutput | ConvertFrom-Json
}
catch {
    Write-Error "Claude's output could not be parsed as JSON."
    exit 3
}

$Blockers = @($Findings.findings | Where-Object { $_.severity -eq "blocker" })

if ($Blockers.Count -gt 0) {
    Write-Host ""
    Write-Host "BLOCKER findings present ($($Blockers.Count)). Failing the build."
    foreach ($b in $Blockers) {
        Write-Host "  - $($b.location.file):$($b.location.line) - $($b.issue)"
    }
    exit 1
}

Write-Host "No blocker findings. Review passed."
exit 0