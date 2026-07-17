param(
    [switch]$Local,
    [switch]$Api,
    [switch]$Web,
    [switch]$Repro
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

$syncArgs = @("sync", "--no-install-project", "--extra", "dev")
if ($Local) {
    $syncArgs += @("--extra", "local")
}
if ($Api) {
    $syncArgs += @("--extra", "api")
}
if ($Web) {
    $syncArgs += @("--extra", "web")
}
if ($Repro) {
    $syncArgs += @("--extra", "repro")
}

& uv @syncArgs
if ($LASTEXITCODE -ne 0) {
    throw "uv dependency sync failed"
}

$wheelDirectory = Join-Path $projectRoot ".wheelhouse"
New-Item -ItemType Directory -Force -Path $wheelDirectory | Out-Null
& uv build --wheel --out-dir $wheelDirectory
if ($LASTEXITCODE -ne 0) {
    throw "wheel build failed"
}

$wheel = Get-ChildItem -LiteralPath $wheelDirectory -Filter "sparsamp_semantic-*.whl" |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
if ($null -eq $wheel) {
    throw "built wheel was not found"
}

& uv pip install --python ".venv\Scripts\python.exe" --force-reinstall --no-deps $wheel.FullName
if ($LASTEXITCODE -ne 0) {
    throw "wheel installation failed"
}

if ($Local) {
    & (Join-Path $PSScriptRoot "install_cuda_torch.ps1")
    if ($LASTEXITCODE -ne 0) {
        throw "CUDA PyTorch installation failed; rerun scripts/install_cuda_torch.ps1 to resume"
    }
}

Write-Output "Environment ready: $($wheel.Name)"
