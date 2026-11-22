@echo off
REM OpenSim Renderer Development Tool
REM Usage: devtool.bat [command] [options]
REM Commands: lint, clean, format, build, test, all

setlocal enabledelayedexpansion
for %%I in ("%~dp0..") do set "PROJECT_DIR=%%~fI"
set "TOOLS_DIR=%PROJECT_DIR%\tools"
set "BUILD_DIR=%PROJECT_DIR%\build"
set "CONDA_ENV_NAME=osim-render"
set "CONDA_CMD="

if "%1"=="" (
    call :show_help
    exit /b 0
)

if /i "%1"=="help" goto :show_help
if /i "%1"=="bootstrap" goto :cmd_bootstrap
if /i "%1"=="lint" goto :cmd_lint
if /i "%1"=="clean" goto :cmd_clean
if /i "%1"=="format" goto :cmd_format
if /i "%1"=="build" goto :cmd_build
if /i "%1"=="run" goto :cmd_run
if /i "%1"=="test" goto :cmd_test
if /i "%1"=="all" goto :cmd_all
if /i "%1"=="install" goto :cmd_install

echo [ERROR] Unknown command: %1
echo Run 'devtool.bat help' for usage information.
exit /b 1

REM =============================================================================
REM COMMAND: lint
REM =============================================================================
:cmd_lint
echo.
echo ===============================================
echo Linting Python code
echo ===============================================
echo.

call :print_status "Running ruff check..."
call :run_poetry run ruff check osim_render tests main.py
if errorlevel 1 (
    call :print_error "Linting failed"
    exit /b 1
)
call :print_success "Linting passed"

call :print_status "Running mypy type check..."
call :run_poetry run mypy osim_render --strict --ignore-missing-imports
if errorlevel 1 (
    call :print_warning "Type checking warnings (non-fatal)"
) else (
    call :print_success "Type checking passed"
)

exit /b 0

REM =============================================================================
REM COMMAND: clean
REM =============================================================================
:cmd_clean
echo.
echo ===============================================
echo Cleaning build artifacts
echo ===============================================
echo.

if exist "%BUILD_DIR%" (
    call :print_status "Removing build directory..."
    rmdir /s /q "%BUILD_DIR%" >nul 2>&1
    call :print_success "Build directory removed"
)

call :print_status "Removing __pycache__ directories..."
for /r "%PROJECT_DIR%" %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d" >nul 2>&1
)
call :print_success "Cache directories removed"

call :print_status "Removing .pytest_cache..."
if exist "%PROJECT_DIR%.pytest_cache" (
    rmdir /s /q "%PROJECT_DIR%.pytest_cache" >nul 2>&1
)
call :print_success ".pytest_cache removed"

exit /b 0

REM =============================================================================
REM COMMAND: format
REM =============================================================================
:cmd_format
echo.
echo ===============================================
echo Formatting Python code
echo ===============================================
echo.

call :print_status "Running ruff format..."
call :run_poetry run ruff format osim_render tests main.py
if errorlevel 1 (
    call :print_error "Formatting failed"
    exit /b 1
)
call :print_success "Code formatted successfully"

exit /b 0

REM =============================================================================
REM COMMAND: build
REM =============================================================================
:cmd_build
echo.
echo ===============================================
echo Building C++ extension
echo ===============================================
echo.

call :cmd_bootstrap
if errorlevel 1 exit /b 1

if not exist "%BUILD_DIR%" (
    call :print_status "Creating build directory..."
    mkdir "%BUILD_DIR%"
)

call :resolve_conda_python
if errorlevel 1 exit /b 1

call :print_status "Running CMake configuration..."
cmake -S "%PROJECT_DIR%" -B "%BUILD_DIR%" -G "Visual Studio 17 2022" -A x64 -DPython3_EXECUTABLE="%CONDA_ENV_PYTHON%"
if errorlevel 1 (
    call :print_error "CMake configuration failed"
    exit /b 1
)
call :print_success "CMake configured"

call :print_status "Building with MSBuild..."
cmake --build "%BUILD_DIR%" --config Release
if errorlevel 1 (
    call :print_error "Build failed"
    exit /b 1
)
call :print_success "Build completed successfully"

REM CMake emits the extension directly into the package directory. The SWIG
REM proxy at osim_render\_osim_render_native.py is checked in and hand-edited,
REM so it is deliberately not overwritten from the build tree.
if not exist "%PROJECT_DIR%\osim_render\_osim_render.pyd" (
    call :print_error "Build succeeded but _osim_render.pyd is not in osim_render\."
    exit /b 1
)
call :print_success "Extension installed to osim_render\_osim_render.pyd"

exit /b 0

REM =============================================================================
REM COMMAND: test
REM =============================================================================
:cmd_test
echo.
echo ===============================================
echo Running tests
echo ===============================================
echo.

call :print_status "Running pytest..."
call :run_poetry run pytest tests/ -v --tb=short
if errorlevel 1 (
    call :print_error "Tests failed"
    exit /b 1
)
call :print_success "All tests passed"

exit /b 0

REM =============================================================================
REM COMMAND: run
REM =============================================================================
:cmd_run
echo.
echo ===============================================
echo Running application
echo ===============================================
echo.

call :cmd_bootstrap
if errorlevel 1 exit /b 1

REM Launch with the Conda interpreter directly, NOT via `poetry run`. Poetry
REM re-resolves the environment for `run`, and an in-project .venv wins that
REM resolution even with virtualenvs.create=false. That .venv carries the PyPI
REM dependencies but not opensim, which comes from Conda -- so `poetry run
REM python main.py` dies on `import opensim` right after a bootstrap that
REM reported success.
call :resolve_conda_python
if errorlevel 1 exit /b 1

call :print_status "Launching main.py with %CONDA_ENV_PYTHON%"
pushd "%PROJECT_DIR%" >nul
"%CONDA_ENV_PYTHON%" main.py %2 %3 %4 %5 %6 %7 %8 %9
set "RUN_EXIT=%ERRORLEVEL%"
popd >nul
exit /b %RUN_EXIT%

REM =============================================================================
REM COMMAND: install
REM =============================================================================
:cmd_install
echo.
echo ===============================================
echo Installing Python dependencies
echo ===============================================
echo.

call :cmd_bootstrap
if errorlevel 1 exit /b 1

exit /b 0

REM =============================================================================
REM COMMAND: bootstrap
REM =============================================================================
:cmd_bootstrap
echo.
echo ===============================================
echo Bootstrapping Conda and Poetry environment
echo ===============================================
echo.

powershell -ExecutionPolicy Bypass -File "%TOOLS_DIR%\build.ps1" -Bootstrap
if errorlevel 1 (
    call :print_error "Bootstrap failed"
    exit /b 1
)
call :print_success "Bootstrap completed"

exit /b 0

REM =============================================================================
REM COMMAND: all
REM =============================================================================
:cmd_all
echo.
echo ===============================================
echo Running all development tools
echo ===============================================
echo.

REM "%~f0" is this script's full path; a bare name would only resolve when the
REM working directory happens to be tools\.
call "%~f0" clean
if errorlevel 1 exit /b 1

call "%~f0" bootstrap
if errorlevel 1 exit /b 1

call "%~f0" build
if errorlevel 1 exit /b 1

call "%~f0" format
if errorlevel 1 exit /b 1

call "%~f0" lint
if errorlevel 1 exit /b 1

call "%~f0" test
if errorlevel 1 exit /b 1

echo.
echo ===============================================
echo All development tasks completed successfully
echo ===============================================
echo.
exit /b 0

REM =============================================================================
REM HELPER FUNCTIONS
REM =============================================================================

:show_help
echo.
echo OpenSim Renderer Development Tool
echo Usage: devtool.bat [command]
echo.
echo Commands:
echo   bootstrap Run Conda + Poetry environment setup from environment.yml
echo   lint      Run linting (ruff check + mypy)
echo   clean     Remove build artifacts and cache
echo   format    Auto-format Python code with ruff
echo   build     Compile C++ extension with CMake
echo   run       Launch main.py in the osim-render Conda environment
echo   test      Run pytest test suite
echo   install   Alias for bootstrap
echo   all       Run all: clean, bootstrap, build, format, lint, test
echo   help      Show this help message
echo.
echo Examples:
echo   devtool.bat bootstrap         - Create Conda env and install dependencies
echo   devtool.bat lint              - Check code style
echo   devtool.bat build             - Compile C++ extension
echo   devtool.bat run               - Start the application with OpenSim available
echo   devtool.bat test              - Run all tests
echo   devtool.bat all               - Full development workflow
echo.
exit /b 0

:run_poetry
REM Invoke Poetry as a module of the environment's interpreter. A bare `poetry`
REM resolves through PATH, where a global Poetry install shadows the one in the
REM environment and would install against its own (wrong) Python.
call :resolve_conda_python
if errorlevel 1 exit /b 1

pushd "%PROJECT_DIR%" >nul
"%CONDA_ENV_PYTHON%" -m poetry %*
set "RUN_EXIT=%ERRORLEVEL%"
popd >nul
exit /b %RUN_EXIT%

:resolve_conda
if defined CONDA_CMD exit /b 0

if defined CONDA_EXE (
    set "CONDA_CMD=%CONDA_EXE%"
    exit /b 0
)

for /f "delims=" %%I in ('where conda.exe 2^>nul') do (
    if not defined CONDA_CMD set "CONDA_CMD=%%I"
)

if not defined CONDA_CMD (
    for /f "delims=" %%I in ('where conda.bat 2^>nul') do (
        if not defined CONDA_CMD set "CONDA_CMD=%%I"
    )
)

if not defined CONDA_CMD (
    call :print_error "Conda was not found on PATH."
    call :print_error "Run 'conda init powershell' once and restart PowerShell,"
    call :print_error "or use an Anaconda Prompt, or set CONDA_EXE to your conda executable path."
    exit /b 1
)

exit /b 0

:resolve_conda_python
REM The extension must be compiled against the interpreter that imports it.
REM Resolve the env prefix from `conda env list` rather than `conda run python`:
REM the latter resolves `python` through PATH and can return an unrelated
REM interpreter (such as a Poetry venv) with an incompatible ABI.
if defined CONDA_ENV_PYTHON exit /b 0

call :resolve_conda
if errorlevel 1 exit /b 1

set "ENV_LIST_TMP=%TEMP%\osim_render_conda_envs.txt"
"%CONDA_CMD%" env list > "%ENV_LIST_TMP%" 2>nul

set "CONDA_ENV_PREFIX="
for /f "usebackq tokens=1,2,3" %%A in ("%ENV_LIST_TMP%") do (
    if /i "%%A"=="%CONDA_ENV_NAME%" (
        if "%%B"=="*" ( set "CONDA_ENV_PREFIX=%%C" ) else ( set "CONDA_ENV_PREFIX=%%B" )
    )
)
if exist "%ENV_LIST_TMP%" erase /q "%ENV_LIST_TMP%" >nul 2>&1

if not defined CONDA_ENV_PREFIX (
    call :print_error "Conda env '%CONDA_ENV_NAME%' not found. Run 'devtool.bat bootstrap' first."
    exit /b 1
)

set "CONDA_ENV_PYTHON=%CONDA_ENV_PREFIX%\python.exe"
if not exist "%CONDA_ENV_PYTHON%" (
    call :print_error "No python.exe in '%CONDA_ENV_PREFIX%'. Recreate it with 'devtool.bat bootstrap'."
    exit /b 1
)

exit /b 0

:print_status
echo [*] %~1
exit /b 0

:print_success
echo [OK] %~1
exit /b 0

:print_warning
echo [!] %~1
exit /b 0

:print_error
echo [ERROR] %~1
exit /b 1
