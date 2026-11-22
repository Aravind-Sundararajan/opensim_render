# PowerShell script to copy geometry files for ToyLandingModel

$repoRoot = Split-Path -Parent $PSScriptRoot
$sourceDir = Join-Path $repoRoot "vendor\opensim-core\Bindings\Java\Matlab\OpenSenseExample\Geometry"
$modelsRoot = if ($env:OSIM_RENDER_MODELS_DIR) { $env:OSIM_RENDER_MODELS_DIR } else { Join-Path $repoRoot "models" }
$targetDir = Join-Path $modelsRoot "toys\ToyDropLanding\Geometry"

# Create target directory if it doesn't exist
if (!(Test-Path $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    Write-Host "Created directory: $targetDir"
}

# Define mapping of source files to target files (with renaming if needed)
$fileMappings = @{
    "sacrum.vtp" = "sacrum.vtp"
    "r_pelvis.vtp" = "pelvis.vtp"
    "l_pelvis.vtp" = "l_pelvis.vtp"
    "femur_r.vtp" = "femur_r.vtp"
    "femur_l.vtp" = "femur_l.vtp"
    "tibia_r.vtp" = "tibia_r.vtp"
    "tibia_l.vtp" = "tibia_l.vtp"
    "r_fibula.vtp" = "fibula.vtp"
    "l_fibula.vtp" = "l_fibula.vtp"
    "r_talus.vtp" = "talus.vtp"
    "l_talus.vtp" = "l_talus.vtp"
    "r_foot.vtp" = "foot.vtp"
    "l_foot.vtp" = "l_foot.vtp"
    "r_bofoot.vtp" = "bofoot.vtp"
    "l_bofoot.vtp" = "l_bofoot.vtp"
    "hat_spine.vtp" = "hat_spine.vtp"
    "hat_jaw.vtp" = "hat_jaw.vtp"
    "hat_skull.vtp" = "hat_skull.vtp"
    "hat_ribs_scap.vtp" = "hat_ribs.vtp"
}

$copied = 0
$failed = 0

foreach ($sourceFile in $fileMappings.Keys) {
    $sourcePath = Join-Path $sourceDir $sourceFile
    $targetFile = $fileMappings[$sourceFile]
    $targetPath = Join-Path $targetDir $targetFile

    if (Test-Path $sourcePath) {
        try {
            Copy-Item -Path $sourcePath -Destination $targetPath -Force
            Write-Host "✓ Copied: $sourceFile -> $targetFile"
            $copied++
        } catch {
            Write-Host "✗ Failed to copy $sourceFile: $_"
            $failed++
        }
    } else {
        Write-Host "✗ Source file not found: $sourceFile"
        $failed++
    }
}

Write-Host ""
Write-Host "Summary:"
Write-Host "  Copied: $copied files"
Write-Host "  Failed: $failed files"
Write-Host ""

if ($failed -eq 0) {
    Write-Host "✓ All geometry files copied successfully!"
    Write-Host "  Location: $targetDir"
} else {
    Write-Host "⚠ Some files could not be copied. Check paths above."
}
