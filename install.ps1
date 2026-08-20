<#
.SYNOPSIS
Installs these skills so Claude Code can find them.

.DESCRIPTION
Claude Code discovers skills at exactly ONE level below a skills directory:

    ~/.claude/skills/<skill-name>/SKILL.md       personal, all your projects
    <repo>/.claude/skills/<skill-name>/SKILL.md  one project only

skills/ holds the starter set and is what you get by default.
extras/ holds the rest, grouped into folders for browsing. Nothing in extras/
installs unless you name it (or pass -All).

Naming a skill also installs whatever that skill calls, because a skill whose
dependencies are missing fails at the point you try to use it.

.EXAMPLE
.\install.ps1
The starter set, for all your projects.

.EXAMPLE
.\install.ps1 -All
Everything, starter set plus extras.

.EXAMPLE
.\install.ps1 code-review wayfinder
The named skills, plus whatever they call.

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
    [switch]$All,
    [Parameter(ValueFromRemainingArguments = $true)][string[]]$Skills
)

$ErrorActionPreference = 'Stop'

function Get-SkillDirs([string]$Path) {
    if (-not (Test-Path $Path)) { return @() }
    Get-ChildItem -Path $Path -Filter 'SKILL.md' -Recurse -File | ForEach-Object { $_.Directory }
}

$starter = @(Get-SkillDirs (Join-Path $PSScriptRoot 'skills'))
$extra   = @(Get-SkillDirs (Join-Path $PSScriptRoot 'extras'))
$every   = $starter + $extra

if ($List) {
    Write-Host "Starter set (installed by default):"
    $starter | ForEach-Object { $_.Name } | Sort-Object | ForEach-Object { Write-Host "  $_" }
    Write-Host ""
    Write-Host "Extras (install by name, or with -All):"
    $extra | ForEach-Object { $_.Name } | Sort-Object | ForEach-Object { Write-Host "  $_" }
    exit 0
}

function Get-Deps($dir) {
    # Skills this one calls, from its `Skill tool with "name"` lines.
    $names = @()
    foreach ($f in Get-ChildItem -Path $dir.FullName -Filter '*.md' -File) {
        foreach ($clause in ([regex]'Skill tool[^.\n]*').Matches((Get-Content $f.FullName -Raw))) {
            foreach ($q in ([regex]'"([a-z][a-z0-9-]*)"').Matches($clause.Value)) {
                $names += $q.Groups[1].Value
            }
        }
    }
    return $names | Sort-Object -Unique
}

$wanted = @()
$pulled = @()

if ($Skills) {
    $wanted = @($Skills)

    # A name that matches nothing is almost always a typo, and silence would hide it.
    foreach ($w in $Skills) {
        if (-not ($every | Where-Object { $_.Name -eq $w })) {
            Write-Warning "No skill named '$w'. Run .\install.ps1 -List to see the names."
        }
    }

    # Pull in whatever the named skills call, transitively.
    $changed = $true
    while ($changed) {
        $changed = $false
        foreach ($name in @($wanted)) {
            $dir = $every | Where-Object { $_.Name -eq $name } | Select-Object -First 1
            if (-not $dir) { continue }
            foreach ($dep in (Get-Deps $dir)) {
                if (($wanted -notcontains $dep) -and ($every | Where-Object { $_.Name -eq $dep })) {
                    $wanted += $dep
                    $pulled += $dep
                    $changed = $true
                }
            }
        }
    }
}

# Default installs the starter set only. Naming skills, or -All, opens up extras.
if ($All -or $Skills) { $sourceDirs = $every } else { $sourceDirs = $starter }

if ($Project) {
    $dest = Join-Path $Project '.claude\skills'
} else {
    $dest = Join-Path $env:USERPROFILE '.claude\skills'
}
New-Item -ItemType Directory -Force -Path $dest | Out-Null

$installed = 0
$replaced = @()

foreach ($dir in $sourceDirs) {
    if ($wanted -and ($wanted -notcontains $dir.Name)) { continue }

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

if ($pulled.Count -gt 0) {
    Write-Host ""
    Write-Host "Also installed, because the skills you named call them:"
    $pulled | Sort-Object -Unique | ForEach-Object { Write-Host "  $_" }
}

if ($replaced.Count -gt 0) {
    Write-Host ""
    Write-Host "Replaced a different skill of the same name:"
    $replaced | ForEach-Object { Write-Host "  $_" }
}

Write-Host ""
Write-Host "Next: start a new Claude Code session, then type /grill-me"
Write-Host "If it autocompletes, the install worked."
Write-Host ""
Write-Host "Add more later with .\install.ps1 <name>, or see them all with -List."

# Only worth saying when it actually applies.
if (Test-Path (Join-Path $dest 'code-review')) {
    Write-Host ""
    Write-Host "Heads-up: code-review overrides Claude Code's built-in /code-review."
    Write-Host "Delete $dest\code-review to get the built-in back."
}
