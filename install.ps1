<#
.SYNOPSIS
Installs these skills so Claude Code can find them.

.DESCRIPTION
Claude Code discovers skills at exactly ONE level below a skills directory:

    ~/.claude/skills/<skill-name>/SKILL.md       personal, all your projects
    <repo>/.claude/skills/<skill-name>/SKILL.md  one project only

This repo groups skills into engineering/ and productivity/ for navigation, so
copying skills/* straight across would install two folders named after the
buckets and nothing would load. This script flattens them.

.EXAMPLE
.\install.ps1
Install everything, for all your projects.

.EXAMPLE
.\install.ps1 grill-me wait-what dbt-test
Install only the named skills.

.EXAMPLE
.\install.ps1 -Project C:\work\our-warehouse
Install into one project instead of your personal skills folder.

.EXAMPLE
.\install.ps1 -List
Show what is available, install nothing.
#>
[CmdletBinding()]
param(
    [string]$Project,
    [switch]$List,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$Skills
)

$ErrorActionPreference = 'Stop'

$sourceDirs = Get-ChildItem -Path (Join-Path $PSScriptRoot 'skills') -Filter 'SKILL.md' -Recurse -File |
    ForEach-Object { $_.Directory }

if ($List) {
    $sourceDirs | ForEach-Object { $_.Name } | Sort-Object
    exit 0
}

if ($Project) {
    $dest = Join-Path $Project '.claude\skills'
} else {
    $dest = Join-Path $env:USERPROFILE '.claude\skills'
}
New-Item -ItemType Directory -Force -Path $dest | Out-Null

$installed = 0
$skipped = 0
$replaced = @()

foreach ($dir in $sourceDirs) {
    if ($Skills -and ($Skills -notcontains $dir.Name)) {
        $skipped++
        continue
    }

    $target = Join-Path $dest $dir.Name
    $targetSkill = Join-Path $target 'SKILL.md'

    # A different copy of this skill is already here: say so before overwriting.
    if (Test-Path $targetSkill) {
        $existingHash = (Get-FileHash $targetSkill).Hash
        $incomingHash = (Get-FileHash (Join-Path $dir.FullName 'SKILL.md')).Hash
        if ($existingHash -ne $incomingHash) { $replaced += $dir.Name }
    }
    if (Test-Path $target) { Remove-Item -Recurse -Force $target }

    Copy-Item -Recurse -Path $dir.FullName -Destination $target
    $installed++
}

Write-Host "Installed $installed skill(s) into $dest"
if ($skipped -gt 0) { Write-Host "Skipped $skipped not named on the command line." }

if ($replaced.Count -gt 0) {
    Write-Host ""
    Write-Host "Replaced an existing skill of the same name:"
    $replaced | ForEach-Object { Write-Host "  $_" }
}

Write-Host ""
Write-Host "Note: a skill installed here overrides a built-in Claude Code command of the"
Write-Host "same name. This set includes ``code-review``, which shadows the bundled"
Write-Host "/code-review. Delete $dest\code-review to get the built-in back."
Write-Host ""
Write-Host "Next: start a new Claude Code session, then type /grill-me"
Write-Host "If it autocompletes, the install worked."
