param(
    [ValidateSet("local", "global")]
    [string]$Scope = "local",
    [string]$TargetProject = (Get-Location).Path
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$SkillSource = Join-Path $RepoRoot ".agents\skills\narrated-video-studio"

if (-not (Test-Path (Join-Path $SkillSource "SKILL.md"))) {
    throw "Skill source not found at: $SkillSource"
}

if ($Scope -eq "local") {
    $DestAgents = Join-Path $TargetProject ".agents\skills\narrated-video-studio"
    $DestClaude = Join-Path $TargetProject ".claude\skills\narrated-video-studio"
    $Targets = @($DestAgents, $DestClaude)
} else {
    $Targets = @(
        (Join-Path $HOME ".agents\skills\narrated-video-studio"),
        (Join-Path $HOME ".claude\skills\narrated-video-studio"),
        (Join-Path $HOME ".gemini\config\skills\narrated-video-studio")
    )
}

foreach ($T in $Targets) {
    New-Item -ItemType Directory -Force -Path $T | Out-Null
    Copy-Item -Path (Join-Path $SkillSource "*") -Destination $T -Recurse -Force
    Write-Output "Installed narrated-video-studio skill to: $T"
}
