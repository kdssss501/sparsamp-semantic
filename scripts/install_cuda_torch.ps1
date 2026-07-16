$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$downloadDirectory = Join-Path $projectRoot ".downloads"
New-Item -ItemType Directory -Force -Path $downloadDirectory | Out-Null

$wheelName = "torch-2.7.1+cu126-cp311-cp311-win_amd64.whl"
$wheelPath = Join-Path $downloadDirectory $wheelName
$wheelUrl = "https://download-r2.pytorch.org/whl/cu126/torch-2.7.1%2Bcu126-cp311-cp311-win_amd64.whl"

& curl.exe `
    --location `
    --fail `
    --retry 20 `
    --retry-delay 5 `
    --retry-all-errors `
    --connect-timeout 30 `
    --continue-at - `
    --output $wheelPath `
    $wheelUrl
if ($LASTEXITCODE -ne 0) {
    throw "CUDA wheel download failed; rerun this script to resume"
}

& uv pip install `
    --python (Join-Path $projectRoot ".venv\Scripts\python.exe") `
    --force-reinstall `
    --no-deps `
    $wheelPath
if ($LASTEXITCODE -ne 0) {
    throw "CUDA wheel installation failed"
}

& (Join-Path $projectRoot ".venv\Scripts\python.exe") -c `
    "import torch; assert torch.cuda.is_available(); print(torch.__version__, torch.cuda.get_device_name(0))"
