#requires -Version 5.1
# Installer-owned profile settings only. Never touches the Firefox installation.
function Set-ThemeUpdaterSettings {
    param([string]$ProfileDirectory, [ValidateSet('Full','Lite')][string]$Edition, [switch]$Disable)
    $path = Join-Path $ProfileDirectory '.whitesur-updater.json'
    if ($Edition -eq 'Lite') {
        Remove-ThemeUpdaterSettings -ProfileDirectory $ProfileDirectory
        return
    }
    $enabled = $Edition -eq 'Full' -and -not $Disable
    $allowPrerelease = $true
    if (Test-Path -LiteralPath $path) {
        if ((Get-Item -LiteralPath $path).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Updater settings are a symbolic link; they were preserved.' }
        $old = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
        if (-not $old.PSObject.Properties['owner'] -or $old.owner -ne 'WhiteSur-Monterey-Adaptive-Windows') { throw 'Unmanaged updater settings were preserved.' }
        if ($old.enabled -isnot [bool]) { throw 'Invalid updater settings were preserved.' }
        if ($Edition -eq 'Full' -and -not $Disable -and $old.edition -eq 'Full') { $enabled = [bool]$old.enabled }
        if ($old.PSObject.Properties['allowPrerelease']) {
            if ($old.allowPrerelease -isnot [bool]) { throw 'Invalid release channel setting was preserved.' }
            $allowPrerelease = $old.allowPrerelease
        }
    }
    @{ schema=1; owner='WhiteSur-Monterey-Adaptive-Windows'; edition=$Edition; enabled=$enabled; allowPrerelease=$allowPrerelease } |
        ConvertTo-Json | Set-Content -LiteralPath $path -Encoding UTF8
}

function Remove-ThemeUpdaterSettings {
    param([string]$ProfileDirectory)
    $path = Join-Path $ProfileDirectory '.whitesur-updater.json'
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return }
    if ((Get-Item -LiteralPath $path).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Updater settings are a symbolic link; they were preserved.' }
    $settings = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
    if ($settings.owner -ne 'WhiteSur-Monterey-Adaptive-Windows') { throw 'Unmanaged updater settings were preserved.' }
    $directory = Join-Path $ProfileDirectory '.whitesur-updates'
    $owner = Join-Path $directory 'owner.json'
    $statePath = Join-Path $directory 'state.json'
    if ((Test-Path -LiteralPath $directory) -and -not ((Get-Item -LiteralPath $directory).Attributes -band [IO.FileAttributes]::ReparsePoint) -and
        (Test-Path -LiteralPath $owner -PathType Leaf) -and (Test-Path -LiteralPath $statePath -PathType Leaf)) {
        foreach ($file in @($owner, $statePath)) {
            if ((Get-Item -LiteralPath $file).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Updater state is a symbolic link; it was preserved.' }
        }
        $directoryOwner = Get-Content -LiteralPath $owner -Raw | ConvertFrom-Json
        $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
        if ($directoryOwner.owner -eq 'WhiteSur-Monterey-Adaptive-Windows' -and $state.owner -eq 'WhiteSur-Monterey-Adaptive-Windows') {
            $state.pending = $null; $state.status = 'disabled'
            $state | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $statePath -Encoding UTF8
        }
    }
    Remove-Item -LiteralPath $path -Force
    # Leave downloaded/rollback files in place. Without the owned Full settings
    # and profile script they cannot apply; do not delete unknown nested files.
}

function Repair-ThemeUpdateTransaction {
    param([string]$ProfileDirectory)
    $profileRoot = [IO.Path]::GetFullPath($ProfileDirectory).TrimEnd('\')
    $chrome = Join-Path $profileRoot 'chrome'
    if (Test-Path -LiteralPath $chrome) { return }
    $directory = Join-Path $profileRoot '.whitesur-updates'
    $journal = Join-Path $directory 'transaction.json'
    if (-not (Test-Path -LiteralPath $journal -PathType Leaf)) { return }
    foreach ($path in @($directory, $journal, (Join-Path $directory 'owner.json'))) {
        if ((Get-Item -LiteralPath $path).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Update recovery paths contain a link; they were preserved.' }
    }
    $owner = Get-Content -LiteralPath (Join-Path $directory 'owner.json') -Raw | ConvertFrom-Json
    $transaction = Get-Content -LiteralPath $journal -Raw | ConvertFrom-Json
    if ($owner.owner -ne 'WhiteSur-Monterey-Adaptive-Windows' -or $transaction.owner -ne $owner.owner -or
        $transaction.backup -notmatch '^rollback-[a-f0-9-]{36}$') { throw 'Unmanaged update recovery files were preserved.' }
    $backup = [IO.Path]::GetFullPath((Join-Path $directory $transaction.backup))
    if ((Split-Path -Parent $backup) -cne $directory) { throw 'Unsafe update recovery path.' }
    $queue = [Collections.Generic.Stack[string]]::new(); $queue.Push($backup)
    while ($queue.Count) {
        $current = Get-Item -LiteralPath $queue.Pop()
        if ($current.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'The update backup contains links and was preserved.' }
        if ($current.PSIsContainer) { Get-ChildItem -LiteralPath $current.FullName -Force | ForEach-Object { $queue.Push($_.FullName) } }
    }
    $marker = Join-Path $backup '.whitesur-monterey-adaptive-windows'
    if (-not (Test-Path -LiteralPath $marker -PathType Leaf) -or [IO.File]::ReadAllText($marker) -notmatch '(?m)^Edition: Full\s*$') { throw 'Update backup ownership could not be verified.' }
    Move-Item -LiteralPath $backup -Destination $chrome
    Remove-Item -LiteralPath $journal -Force
    Write-Status 'Recovered the previous Full theme after an interrupted update.' Yellow
}
