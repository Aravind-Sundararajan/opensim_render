@echo off
REM Batch script to copy geometry files for ToyLandingModel

for %%I in ("%~dp0..") do set "REPO_ROOT=%%~fI"
set "SOURCE_DIR=%REPO_ROOT%\vendor\opensim-core\Bindings\Java\Matlab\OpenSenseExample\Geometry"
if defined OSIM_RENDER_MODELS_DIR (
    set "MODELS_ROOT=%OSIM_RENDER_MODELS_DIR%"
) else (
    set "MODELS_ROOT=%REPO_ROOT%\models"
)
set "TARGET_DIR=%MODELS_ROOT%\toys\ToyDropLanding\Geometry"

REM Create target directory
if not exist "%TARGET_DIR%" (
    mkdir "%TARGET_DIR%"
    echo Created directory: %TARGET_DIR%
)

REM Copy files with potential renaming
echo Copying geometry files...

copy "%SOURCE_DIR%\sacrum.vtp" "%TARGET_DIR%\sacrum.vtp" /Y
copy "%SOURCE_DIR%\r_pelvis.vtp" "%TARGET_DIR%\pelvis.vtp" /Y
copy "%SOURCE_DIR%\l_pelvis.vtp" "%TARGET_DIR%\l_pelvis.vtp" /Y
copy "%SOURCE_DIR%\femur_r.vtp" "%TARGET_DIR%\femur_r.vtp" /Y
copy "%SOURCE_DIR%\femur_l.vtp" "%TARGET_DIR%\femur_l.vtp" /Y
copy "%SOURCE_DIR%\tibia_r.vtp" "%TARGET_DIR%\tibia_r.vtp" /Y
copy "%SOURCE_DIR%\tibia_l.vtp" "%TARGET_DIR%\tibia_l.vtp" /Y
copy "%SOURCE_DIR%\r_fibula.vtp" "%TARGET_DIR%\fibula.vtp" /Y
copy "%SOURCE_DIR%\l_fibula.vtp" "%TARGET_DIR%\l_fibula.vtp" /Y
copy "%SOURCE_DIR%\r_talus.vtp" "%TARGET_DIR%\talus.vtp" /Y
copy "%SOURCE_DIR%\l_talus.vtp" "%TARGET_DIR%\l_talus.vtp" /Y
copy "%SOURCE_DIR%\r_foot.vtp" "%TARGET_DIR%\foot.vtp" /Y
copy "%SOURCE_DIR%\l_foot.vtp" "%TARGET_DIR%\l_foot.vtp" /Y
copy "%SOURCE_DIR%\r_bofoot.vtp" "%TARGET_DIR%\bofoot.vtp" /Y
copy "%SOURCE_DIR%\l_bofoot.vtp" "%TARGET_DIR%\l_bofoot.vtp" /Y
copy "%SOURCE_DIR%\hat_spine.vtp" "%TARGET_DIR%\hat_spine.vtp" /Y
copy "%SOURCE_DIR%\hat_jaw.vtp" "%TARGET_DIR%\hat_jaw.vtp" /Y
copy "%SOURCE_DIR%\hat_skull.vtp" "%TARGET_DIR%\hat_skull.vtp" /Y
copy "%SOURCE_DIR%\hat_ribs_scap.vtp" "%TARGET_DIR%\hat_ribs.vtp" /Y

REM Verify
cd /d "%TARGET_DIR%"
echo.
echo Geometry files in target directory:
dir /B *.vtp
echo.
echo Done! Geometry files have been copied to:
echo %TARGET_DIR%
