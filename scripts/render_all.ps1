<#
.SYNOPSIS
    Render all animation scripts to MP4 files.

.DESCRIPTION
    Runs render_animation_scripts.py for every animation script in animation_scripts/.
    Automatically detects the correct model and geometry paths from each script's docstring.
    You can override any of these via parameters.

.PARAMETER Model
    Override model path for all scripts. If not specified, uses the model
    documented in each script's USAGE section.

.PARAMETER GeometryPath
    Override geometry search directories. Can be passed multiple times.
    If not specified, uses the geometry paths from each script's USAGE section.

.PARAMETER DefaultModel
    Fallback model to use if a script doesn't specify one in its docstring.
    Default: models\lowerExtremity\Gait2392_Simbody\gait2392_simbody.osim

.PARAMETER DefaultGeometryPath
    Fallback geometry paths when script doesn't specify any.
    Default: C:\OpenSim 4.5\Geometry

.PARAMETER OutputDir
    Directory to write MP4 files into.
    Default: renders\

.PARAMETER Fps
    Frames per second. Default: 30

.PARAMETER Width
    Output width in pixels. Default: 1280

.PARAMETER Height
    Output height in pixels. Default: 720

.PARAMETER Quality
    Video quality: high | medium | low. Default: medium

.PARAMETER PlaybackSpeed
    Playback speed multiplier. Default: 1.0
    Examples: 0.2 = 5x slower, 0.5 = half speed, 2.0 = 2x faster

.PARAMETER Scripts
    Only render scripts whose filename contains these substrings.
    E.g. -Scripts 01,V01 to render 01_basic and V01_visualizations.

.EXAMPLE
    .\scripts\render_all.ps1

.EXAMPLE
    .\scripts\render_all.ps1 -DefaultModel models\lowerExtremity\Gait2354_Simbody\gait2354_simbody.osim

.EXAMPLE
    .\scripts\render_all.ps1 -Scripts 01,08,11 -Quality high -Width 1920 -Height 1080

.EXAMPLE
    .\scripts\render_all.ps1 -PlaybackSpeed 0.2

.EXAMPLE
    .\scripts\render_all.ps1 -Model models\chimp_fullbody\model.osim -GeometryPath "models\chimp_fullbody\Geometry"
#>

[CmdletBinding()]
param(
    [string]   $Model              = "",
    [string[]] $GeometryPath       = @(),
    [string]   $DefaultModel       = "models\lowerExtremity\Gait2392_Simbody\gait2392_simbody.osim",
    [string[]] $DefaultGeometryPath = @("C:\OpenSim 4.5\Geometry"),
    [string]   $OutputDir          = "renders",
    [int]      $Fps                = 30,
    [int]      $Width              = 1280,
    [int]      $Height             = 720,
    [ValidateSet("high","medium","low")]
    [string]   $Quality            = "medium",
    [double]   $PlaybackSpeed      = 1.0,
    [string[]] $Scripts            = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Resolve repo root (parent of this script's directory) ────────────────────
$RepoRoot = Split-Path -Parent $PSScriptRoot

# ── Helper function: Extract model path from script docstring ────────────────
function Get-ModelFromScript {
    param([string]$ScriptPath)
    
    $content = Get-Content $ScriptPath -Raw
    
    # Try double-quoted paths first
    if ($content -match '--model\s+"([^"]+)"') {
        return $matches[1]
    }
    
    # Try single-quoted paths
    if ($content -match "--model\s+'([^']+)'") {
        return $matches[1]
    }
    
    # Try unquoted paths (exclude quotes, may have trailing backslash from line continuation)
    if ($content -match '--model\s+([^\s"''\\]+)') {
        $modelPath = $matches[1]
        return $modelPath
    }
    
    return $null
}

# ── Helper function: Extract geometry paths from script docstring ────────────
function Get-GeometryPathsFromScript {
    param([string]$ScriptPath)
    
    $paths = @()
    $content = Get-Content $ScriptPath -Raw
    
    # Try double-quoted paths first
    $quotedMatches = [regex]::Matches($content, '-g\s+"([^"]+)"')
    foreach ($match in $quotedMatches) {
        $paths += $match.Groups[1].Value
    }
    
    # Try single-quoted paths
    $singleQuotedMatches = [regex]::Matches($content, "-g\s+'([^']+)'")
    foreach ($match in $singleQuotedMatches) {
        if ($paths -notcontains $match.Groups[1].Value) {
            $paths += $match.Groups[1].Value
        }
    }
    
    # Try unquoted paths (exclude quotes, may have trailing backslash)
    # Pattern: -g followed by whitespace, then non-whitespace chars that don't start with quotes
    $unquotedMatches = [regex]::Matches($content, '-g\s+([^\s"'']+)')
    foreach ($match in $unquotedMatches) {
        $path = $match.Groups[1].Value.TrimEnd('\')
        # Avoid duplicates from quoted matches
        if ($paths -notcontains $path) {
            $paths += $path
        }
    }
    
    # Ensure we always return an array (PowerShell quirk: @() forces array context)
    return @($paths)
}

# ── Get list of scripts to render ─────────────────────────────────────────────
$ScriptsDir = Join-Path $RepoRoot "animation_scripts"
$AllScripts = Get-ChildItem -Path $ScriptsDir -Filter "*.py" | Where-Object { 
    $_.Name -notmatch "^__" 
} | Sort-Object Name

if (@($Scripts).Count -gt 0) {
    $ScriptsToRender = @($AllScripts | Where-Object {
        $name = $_.Name
        $Scripts | Where-Object { $name -like "*$_*" }
    })
    if (@($ScriptsToRender).Count -eq 0) {
        Write-Error "No scripts matched: $($Scripts -join ', ')"
        exit 1
    }
} else {
    $ScriptsToRender = $AllScripts
}

# ── Resolve output directory ──────────────────────────────────────────────────
$OutputPath = Join-Path $RepoRoot $OutputDir
New-Item -ItemType Directory -Force -Path $OutputPath | Out-Null

# ── Print summary ─────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=== render_all ===" -ForegroundColor Cyan
Write-Host "  Resolution : ${Width}x${Height} @ ${Fps}fps  quality=$Quality  speed=${PlaybackSpeed}x"
Write-Host "  Output     : $OutputPath"
if ($Model) {
    Write-Host "  Override   : Model=$Model (all scripts)"
}
if (@($GeometryPath).Count -gt 0) {
    Write-Host "  Override   : Geometry=$($GeometryPath -join ', ') (all scripts)"
}
if (@($Scripts).Count -gt 0) {
    Write-Host "  Filter     : $($Scripts -join ', ')"
}
Write-Host "  Scripts    : $($ScriptsToRender.Count) script(s)"
Write-Host ""

# ── Process each script ───────────────────────────────────────────────────────
$PyScript = Join-Path $RepoRoot "scripts\render_animation_scripts.py"
$SuccessCount = 0
$FailedScripts = @()

Push-Location $RepoRoot
try {
    for ($i = 0; $i -lt $ScriptsToRender.Count; $i++) {
        $script = $ScriptsToRender[$i]
        $num = $i + 1
        
        Write-Host "[$num/$($ScriptsToRender.Count)] $($script.Name)" -ForegroundColor Yellow
        
        # Determine model for this script
        $scriptModel = if ($Model) { 
            $Model 
        } else {
            $detected = Get-ModelFromScript $script.FullName
            if ($detected) { $detected } else { $DefaultModel }
        }
        
        # Resolve to absolute path
        if (-not [System.IO.Path]::IsPathRooted($scriptModel)) {
            $scriptModel = Join-Path $RepoRoot $scriptModel
        }
        
        if (-not (Test-Path $scriptModel)) {
            Write-Host "  SKIPPED: Model not found: $scriptModel" -ForegroundColor Red
            $FailedScripts += $script.Name
            Write-Host ""
            continue
        }
        
        # Determine geometry paths for this script
        $scriptGeometry = if (@($GeometryPath).Count -gt 0) {
            $GeometryPath
        } else {
            $detected = Get-GeometryPathsFromScript $script.FullName
            # Use detected paths if any were found, otherwise use defaults
            if (($detected -ne $null) -and (@($detected).Count -gt 0)) { 
                $detected 
            } else { 
                $DefaultGeometryPath 
            }
        }
        
        # Resolve geometry paths to absolute
        $resolvedGeometry = @()
        foreach ($g in $scriptGeometry) {
            if (-not [System.IO.Path]::IsPathRooted($g)) {
                $g = Join-Path $RepoRoot $g
            }
            $resolvedGeometry += $g
        }
        
        # Build arguments
        $Args = @(
            $PyScript,
            "--model", $scriptModel,
            "--output-dir", $OutputPath,
            "--fps", $Fps,
            "--resolution", $Width, $Height,
            "--quality", $Quality,
            "--playback-speed", $PlaybackSpeed,
            "--scripts", $script.BaseName
        )
        
        foreach ($g in $resolvedGeometry) {
            $Args += "--geometry-path", $g
        }
        
        Write-Host "  Model: $scriptModel" -ForegroundColor Gray
        if (@($resolvedGeometry).Count -gt 0) {
            Write-Host "  Geometry: $($resolvedGeometry -join ', ')" -ForegroundColor Gray
        }
        
        # Execute
        poetry run python @Args
        
        if ($LASTEXITCODE -eq 0) {
            $SuccessCount++
        } else {
            $FailedScripts += $script.Name
        }
        
        Write-Host ""
    }
} finally {
    Pop-Location
}

# ── Summary ──────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "  Succeeded: $SuccessCount / $(@($ScriptsToRender).Count)"
if (@($FailedScripts).Count -gt 0) {
    Write-Host "  Failed: $($FailedScripts -join ', ')" -ForegroundColor Red
    exit 1
} else {
    Write-Host "  All scripts rendered successfully!" -ForegroundColor Green
    exit 0
}
