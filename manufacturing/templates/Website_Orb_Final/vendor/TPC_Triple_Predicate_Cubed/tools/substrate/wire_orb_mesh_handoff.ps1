param(
    [string]$MeshLinkPath = "R:\orb_mesh\tpc_handoffs",
    [string]$TargetPath = "R:\tpc_substrate\orb_handoffs"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $TargetPath)) {
    New-Item -ItemType Directory -Path $TargetPath -Force | Out-Null
}

if (Test-Path $MeshLinkPath) {
    $item = Get-Item $MeshLinkPath -Force
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        Write-Output "Link already exists: $MeshLinkPath"
        exit 0
    }

    if ($item.PSIsContainer) {
        $entries = Get-ChildItem -Path $MeshLinkPath -Force
        if ($entries.Count -gt 0) {
            throw "Existing directory at $MeshLinkPath is not empty. Refusing to replace it."
        }
        Remove-Item -Path $MeshLinkPath -Force
    } else {
        throw "Existing file at $MeshLinkPath blocks link creation."
    }
}

New-Item -ItemType SymbolicLink -Path $MeshLinkPath -Target $TargetPath | Out-Null
Write-Output "Created symbolic link: $MeshLinkPath -> $TargetPath"
