# OpenSim Renderer build script for Windows PowerShell

param(
    [switch]$All = $false,
    [switch]$Bootstrap = $false,
    [switch]$Build = $false,
    [switch]$Install = $false,
    [switch]$Run = $false,
    [switch]$Clean = $false,
    [switch]$Test = $false
)

$ErrorActionPreference = "Stop"
$CondaEnvironmentName = "osim-render"
$RepoRoot = Split-Path -Parent $PSScriptRoot

function Write-Header {
    param([string]$message)
    Write-Host ""
    Write-Host "===============================================" -ForegroundColor Cyan
    Write-Host $message -ForegroundColor Cyan
    Write-Host "===============================================" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Status {
    param([string]$message)
    Write-Host "[*] $message" -ForegroundColor Gray
}

function Write-Success {
    param([string]$message)
    Write-Host "[OK] $message" -ForegroundColor Green
}

function Write-Error {
    param([string]$message)
    Write-Host "[ERROR] $message" -ForegroundColor Red
}

function Get-CondaCommand {
    if ($env:CONDA_EXE) {
        return $env:CONDA_EXE
    }

    $condaCommand = Get-Command conda -ErrorAction SilentlyContinue
    if ($condaCommand) {
        return $condaCommand.Source
    }

    throw (
        "Conda was not found on PATH. Run 'conda init powershell' once and restart PowerShell, " +
        "or use an Anaconda Prompt, or set CONDA_EXE to your conda executable path."
    )
}

function Invoke-CondaCommand {
    param([string[]]$Arguments)

    $condaCommand = Get-CondaCommand
    & $condaCommand @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Conda command failed: conda $($Arguments -join ' ')"
    }
}

function Test-CondaEnvironmentExists {
    $condaCommand = Get-CondaCommand
    $jsonOutput = & $condaCommand env list --json
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to query Conda environments."
    }

    $environmentInfo = $jsonOutput | ConvertFrom-Json
    foreach ($environmentPath in $environmentInfo.envs) {
        if ((Split-Path $environmentPath -Leaf) -eq $CondaEnvironmentName) {
            return $true
        }
    }

    return $false
}

function Get-CondaEnvironmentPython {
    # The extension must be compiled against the interpreter that imports it.
    # `conda run python` resolves through PATH and can return an unrelated
    # interpreter, so read the environment prefix directly.
    $condaCommand = Get-CondaCommand
    $jsonOutput = & $condaCommand env list --json
    if ($LASTEXITCODE -ne 0) {
        throw "Unable to query Conda environments."
    }

    $environmentInfo = $jsonOutput | ConvertFrom-Json
    foreach ($environmentPath in $environmentInfo.envs) {
        if ((Split-Path $environmentPath -Leaf) -eq $CondaEnvironmentName) {
            $pythonPath = Join-Path $environmentPath "python.exe"
            if (-not (Test-Path $pythonPath)) {
                throw "No python.exe in Conda environment '$environmentPath'."
            }
            return $pythonPath
        }
    }

    throw "Conda environment '$CondaEnvironmentName' not found. Run build.ps1 -Bootstrap first."
}

function Invoke-RepoPoetry {
    param([string[]]$Arguments)

    # Invoke Poetry as a module of the environment's interpreter. A bare `poetry`
    # resolves through PATH, where a global Poetry install shadows the one in the
    # environment and would install against its own (wrong) Python.
    $python = Get-CondaEnvironmentPython

    Push-Location $RepoRoot
    try {
        & $python -m poetry @Arguments

        if ($LASTEXITCODE -ne 0) {
            throw "Poetry command failed: poetry $($Arguments -join ' ')"
        }
    } finally {
        Pop-Location
    }
}

function Invoke-Bootstrap {
    Write-Header "Bootstrapping Conda and Poetry environment"

    if (-not (Test-CondaEnvironmentExists)) {
        Write-Status "Creating Conda environment from environment.yml..."
        Invoke-CondaCommand @("env", "create", "-f", (Join-Path $RepoRoot "environment.yml"))
        Write-Success "Conda environment created"
    } else {
        Write-Status "Conda environment '$CondaEnvironmentName' already exists"
    }

    Write-Status "Configuring Poetry to use the active Conda environment..."
    Invoke-RepoPoetry @("config", "virtualenvs.create", "false", "--local")
    Write-Success "Poetry configured"

    Write-Status "Installing Python dependencies with Poetry..."
    Invoke-RepoPoetry @("install")
    Write-Success "Dependencies installed"
}

# Default to all steps if no flags provided. -Run is included so that
# `build.ps1 -Run` launches the app instead of triggering a full rebuild.
if (-not $All -and -not $Bootstrap -and -not $Build -and -not $Install -and -not $Clean -and -not $Test -and -not $Run) {
    $All = $true
}

if ($All) {
    $Bootstrap = $true
    $Clean = $true
    $Build = $true
    $Install = $true
    $Test = $true
}

try {
    Push-Location $RepoRoot

    if ($Bootstrap) {
        Invoke-Bootstrap
        Write-Host ""
        # NOT `poetry run python main.py`. Poetry re-resolves the environment
        # for `run` and an in-project .venv wins even with
        # virtualenvs.create=false -- that .venv has the PyPI dependencies but
        # not opensim, which comes from Conda.
        Write-Host "Use one of these to run the app with OpenSim available:" -ForegroundColor Cyan
        Write-Host "  conda activate $CondaEnvironmentName" -ForegroundColor Cyan
        Write-Host "  python main.py" -ForegroundColor Cyan
        Write-Host "or:" -ForegroundColor Cyan
        Write-Host "  tools\devtool.bat run" -ForegroundColor Cyan
    }

    # Clean
    if ($Clean) {
        Write-Header "Cleaning build artifacts"
        if (Test-Path "build") {
            Remove-Item -Recurse -Force "build" -ErrorAction SilentlyContinue
            Write-Success "Removed build directory"
        }
    }

    # Build
    if ($Build) {
        Write-Header "Building C++ extension with CMake"

        $buildDir = Join-Path $RepoRoot "build"
        $condaPython = Get-CondaEnvironmentPython

        Write-Status "Running CMake configuration against $condaPython..."
        cmake -S $RepoRoot -B $buildDir -G "Visual Studio 17 2022" -A x64 `
            "-DPython3_EXECUTABLE=$condaPython"
        if ($LASTEXITCODE -ne 0) {
            throw "CMake configuration failed"
        }

        Write-Status "Building with MSBuild..."
        cmake --build $buildDir --config Release
        if ($LASTEXITCODE -ne 0) {
            throw "CMake build failed"
        }

        # CMake writes the extension straight into the package directory.
        $extension = Join-Path $RepoRoot "osim_render\_osim_render.pyd"
        if (-not (Test-Path $extension)) {
            throw "Build succeeded but $extension is missing"
        }

        Write-Success "Build completed; extension at $extension"
    }

    # Install
    if ($Install) {
        Write-Header "Installing Python package"

        Write-Status "Installing with Poetry..."
        Invoke-RepoPoetry @("install")

        Write-Success "Package installed"
    }

    # Test
    if ($Test) {
        Write-Header "Running tests"

        Write-Status "Running pytest..."
        Invoke-RepoPoetry @("run", "pytest", "tests/", "-v")

        Write-Success "Tests completed"
    }

    if ($Run) {
        Write-Header "Running application"

        # Launch with the Conda interpreter directly, NOT via `poetry run`.
        # Poetry re-resolves the environment for `run`, and an in-project
        # .venv wins that resolution even with virtualenvs.create=false. That
        # .venv has the PyPI dependencies but not opensim, which comes from
        # Conda, so `poetry run python main.py` dies on `import opensim` after
        # a bootstrap that reported success.
        $condaPython = Get-CondaEnvironmentPython
        Write-Status "Launching main.py with $condaPython"

        Push-Location $RepoRoot
        try {
            & $condaPython main.py
            if ($LASTEXITCODE -ne 0) {
                throw "Application exited with code $LASTEXITCODE"
            }
        } finally {
            Pop-Location
        }
    }

    Write-Header "Build completed successfully"
    exit 0

} catch {
    Write-Error "Build failed: $_"
    exit 1
} finally {
    Pop-Location
}
