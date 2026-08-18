# Copy the gates into a repo and wire the hook (Windows).
#
#   .\install.ps1 C:\path\to\your-repo

param([Parameter(Mandatory = $true)][string]$Target)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path

$scripts = Join-Path $Target "scripts"
New-Item -ItemType Directory -Force -Path $scripts | Out-Null
Copy-Item (Join-Path $here "gates\*.py") $scripts -Force

$frozen = Join-Path $Target "frozen.json"
if (-not (Test-Path $frozen)) {
    Copy-Item (Join-Path $here "examples\frozen.json") $frozen
}

$policy = Join-Path $Target "git_policy.json"
if (-not (Test-Path $policy)) {
    Copy-Item (Join-Path $here "examples\git_policy.json") $policy
}

$guardrailPolicy = Join-Path $Target "guardrail_policy.json"
if (-not (Test-Path $guardrailPolicy)) {
    Copy-Item (Join-Path $here "examples\guardrail_policy.json") $guardrailPolicy
}

$hook = Join-Path $Target ".git\hooks\pre-commit"
Copy-Item (Join-Path $here "hooks\pre-commit") $hook -Force
$commitMsgHook = Join-Path $Target ".git\hooks\commit-msg"
Copy-Item (Join-Path $here "hooks\commit-msg") $commitMsgHook -Force

Write-Host "Installed."
Write-Host "Start with an empty frozen list. Add the first path the day an agent"
Write-Host "edits something you thought was finished."
Write-Host "Optional task scope: copy examples\scope.json to .agent-guardrails\scope.json."
