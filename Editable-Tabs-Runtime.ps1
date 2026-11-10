#requires -Version 5.1
# Shared installer functions; dot-sourced by the package installer.

function Get-EditableTabsStatePath {
    param([string]$ProfileDirectory)
    return (Join-Path $ProfileDirectory '.whitesur-editable-tabs.json')
}

function Find-FirefoxExecutable {
    param([string]$RequestedPath)
    if (-not [string]::IsNullOrWhiteSpace($RequestedPath)) {
        $candidate = if (Test-Path -LiteralPath $RequestedPath -PathType Container) {
            Join-Path $RequestedPath 'firefox.exe'
        } else { $RequestedPath }
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            throw "Firefox executable does not exist: $candidate"
        }
        return (Resolve-Path -LiteralPath $candidate).Path
    }
    $candidates = [System.Collections.Generic.List[string]]::new()
    foreach ($key in @('HKCU:\Software\Microsoft\Windows\CurrentVersion\App Paths\firefox.exe',
                       'HKLM:\Software\Microsoft\Windows\CurrentVersion\App Paths\firefox.exe')) {
        if (Test-Path -LiteralPath $key) {
            $value = (Get-Item -LiteralPath $key).GetValue('')
            if ($value) { $candidates.Add([string]$value) }
        }
    }
    foreach ($folder in @($env:ProgramFiles, [Environment]::GetEnvironmentVariable('ProgramFiles(x86)'),
                          (Join-Path $env:LOCALAPPDATA 'Programs'))) {
        if ($folder) { $candidates.Add((Join-Path $folder 'Mozilla Firefox\firefox.exe')) }
    }
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    return $null
}

function Get-FirefoxRuntimeVersion {
    param([string]$Executable)
    $ini = Join-Path (Split-Path -Parent $Executable) 'application.ini'
    if (Test-Path -LiteralPath $ini -PathType Leaf) {
        $text = [IO.File]::ReadAllText($ini)
        if ($text -match '(?m)^Version=(\d+(?:\.\d+){0,3})\s*$') {
            return [version]$Matches[1]
        }
    }
    $versionText = (Get-Item -LiteralPath $Executable).VersionInfo.FileVersion
    if ($versionText -match '\d+(?:\.\d+){1,3}') { return [version]$Matches[0] }
    return [version]'0.0'
}

function Test-ForeignAutoConfig {
    param([string]$Directory)
    $owned = $false
    foreach ($markerName in @('.whitesur-runtime.json', '.whitesur-loader.json')) {
        $ownershipFile = Join-Path $Directory $markerName
        if (Test-Path -LiteralPath $ownershipFile -PathType Leaf) {
            $ownership = Get-Content -LiteralPath $ownershipFile -Raw | ConvertFrom-Json
            if ($ownership.Owner -eq 'WhiteSur-Monterey-Adaptive-Windows') { $owned = $true }
        }
    }
    $prefDirectory = Join-Path $Directory 'defaults\pref'
    foreach ($file in @(Get-ChildItem -LiteralPath $prefDirectory -Filter '*.js' -File -ErrorAction SilentlyContinue)) {
        $text = [IO.File]::ReadAllText($file.FullName)
        $pattern = '(?m)^\s*(?:pref|defaultPref|lockPref)\s*\(\s*["'']general\.config\.filename["'']\s*,\s*["'']([^"'']+)["'']'
        foreach ($match in [regex]::Matches($text, $pattern)) {
            if ($match.Groups[1].Value -ne 'whitesur.cfg' -or -not $owned) { return $true }
        }
    }
    return $false
}

function Install-EditableTabsLoader {
    param([Parameter(Mandatory)][string]$Directory)
    if (-not (Test-Path -LiteralPath (Join-Path $Directory 'firefox.exe') -PathType Leaf)) {
        throw 'The selected Firefox installation does not contain firefox.exe.'
    }
    foreach ($path in @($Directory, (Join-Path $Directory 'defaults'), (Join-Path $Directory 'defaults\pref'))) {
        if ((Test-Path -LiteralPath $path) -and ((Get-Item -LiteralPath $path).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw 'The Firefox loader directory must not be a junction or symbolic link.'
        }
    }
    if (Test-ForeignAutoConfig -Directory $Directory) { throw 'Existing Firefox AutoConfig was preserved.' }
    $markerPath = Join-Path $Directory '.whitesur-loader.json'
    $owned = $false
    if (Test-Path -LiteralPath $markerPath -PathType Leaf) {
        $marker = Get-Content -LiteralPath $markerPath -Raw | ConvertFrom-Json
        if ($marker.Owner -ne 'WhiteSur-Monterey-Adaptive-Windows') { throw 'The loader ownership marker is invalid.' }
        $owned = $true
    }
    foreach ($relative in @('.whitesur-loader.json', 'whitesur.cfg', 'defaults\pref\whitesur-autoconfig.js')) {
        $target = Join-Path $Directory $relative
        if (Test-Path -LiteralPath $target) {
            if ((Get-Item -LiteralPath $target).Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw 'A Firefox loader file is a symbolic link; it was left untouched.'
            }
            if (-not $owned) { throw "Refusing to overwrite an unmanaged Firefox loader file: $target" }
        }
    }
    # Reserve only our loader files. Firefox itself and its other files are not copied.
    @{ Owner='WhiteSur-Monterey-Adaptive-Windows'; Ready=$false } |
        ConvertTo-Json | Set-Content -LiteralPath $markerPath -Encoding UTF8
    foreach ($relative in @('whitesur.cfg', 'defaults\pref\whitesur-autoconfig.js')) {
        $source = Join-Path (Join-Path $PackageRoot 'firefox') $relative
        $target = Join-Path $Directory $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $target) -Force | Out-Null
        [IO.File]::WriteAllText($target, [IO.File]::ReadAllText($source).Replace("`r`n", "`n"), [Text.UTF8Encoding]::new($false))
    }
    @{ Owner='WhiteSur-Monterey-Adaptive-Windows'; Ready=$true } |
        ConvertTo-Json | Set-Content -LiteralPath $markerPath -Encoding UTF8
}

function Initialize-EditableTabsRuntime {
    param([string]$SourceExecutable, [string]$DestinationDirectory, [switch]$Classic)
    if ($Classic) { return [pscustomobject]@{ Enabled=$false; Executable=$null; Reason='CSS-only mode requested.' } }
    $executable = Find-FirefoxExecutable -RequestedPath $SourceExecutable
    if (-not $executable) {
        return [pscustomobject]@{ Enabled=$false; Executable=$null; Reason='Firefox was not found.' }
    }
    $sourceVersion = Get-FirefoxRuntimeVersion -Executable $executable
    if ($sourceVersion.Major -lt 158) {
        return [pscustomobject]@{ Enabled=$false; Executable=$null; Reason="Firefox $sourceVersion is unsupported. Editable tabs require Firefox 158+." }
    }
    $sourceDirectory = Split-Path -Parent $executable
    if (Test-ForeignAutoConfig -Directory $sourceDirectory) {
        return [pscustomobject]@{ Enabled=$false; Executable=$null; Reason='Existing Firefox AutoConfig detected; choose a clean Firefox installation with -FirefoxPath.' }
    }
    if ([string]::IsNullOrWhiteSpace($DestinationDirectory)) {
        try {
            Install-EditableTabsLoader -Directory $sourceDirectory
        } catch [System.UnauthorizedAccessException], [System.Security.SecurityException] {
            Write-Status 'Windows administrator approval is required to add the editable-tab loader to your existing Firefox.' Yellow
            $helper = Join-Path $PackageRoot 'Install-Editable-Tabs-Loader.ps1'
            $arguments = '-NoLogo -NoProfile -ExecutionPolicy Bypass -File "' + $helper + '" -FirefoxDirectory "' + $sourceDirectory + '"'
            $result = Start-Process -FilePath (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') -ArgumentList $arguments -Verb RunAs -WindowStyle Hidden -Wait -PassThru
            if ($result.ExitCode -ne 0) { throw 'Firefox loader setup failed. Run Install.cmd again and approve the Windows administrator prompt.' }
        }
        foreach ($relative in @('whitesur.cfg', 'defaults\pref\whitesur-autoconfig.js')) {
            $expected = [IO.File]::ReadAllText((Join-Path (Join-Path $PackageRoot 'firefox') $relative)).Replace("`r`n", "`n")
            if ([IO.File]::ReadAllText((Join-Path $sourceDirectory $relative)) -cne $expected) {
                throw 'Firefox loader verification failed; the profile theme was not changed.'
            }
        }
        return [pscustomobject]@{ Enabled=$true; InPlace=$true; Executable=$executable; Reason='Editable tabs enabled in your existing Firefox. Your usual Firefox shortcuts work.' }
    }
    $destination = [IO.Path]::GetFullPath($DestinationDirectory).TrimEnd('\')
    $sourceDirectory = [IO.Path]::GetFullPath($sourceDirectory).TrimEnd('\')
    $sameDirectory = Test-PathEquals -Left $sourceDirectory -Right $destination
    if (-not $sameDirectory -and
        ($destination.StartsWith($sourceDirectory + '\', [StringComparison]::OrdinalIgnoreCase) -or
        $sourceDirectory.StartsWith($destination + '\', [StringComparison]::OrdinalIgnoreCase))) {
        throw 'The WhiteSur runtime must be separate from the source Firefox installation.'
    }
    $markerPath = Join-Path $destination '.whitesur-runtime.json'
    $runtimeReady = $false
    if (Test-Path -LiteralPath $destination) {
        if ((Get-Item -LiteralPath $destination).Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw 'The WhiteSur runtime directory must not be a junction or symbolic link.'
        }
        if (-not (Test-Path -LiteralPath $markerPath -PathType Leaf)) {
            if (@(Get-ChildItem -LiteralPath $destination -Force).Count -gt 0) {
                throw "Refusing to overwrite an unmanaged directory: $destination"
            }
        } else {
            $marker = Get-Content -LiteralPath $markerPath -Raw | ConvertFrom-Json
            if ($marker.Owner -ne 'WhiteSur-Monterey-Adaptive-Windows') { throw 'The runtime ownership marker is invalid.' }
            $runtimeReady = $marker.Ready -eq $true
        }
        if (Test-ForeignAutoConfig -Directory $destination) { throw 'The runtime contains another AutoConfig; it was left untouched.' }
    }
    if ($sameDirectory -and -not $runtimeReady) {
        throw 'The source can only be reused in place when it is a completed WhiteSur runtime.'
    }
    New-Item -ItemType Directory -Path $destination -Force | Out-Null
    $targetExecutable = Join-Path $destination 'firefox.exe'
    $copySource = -not $runtimeReady -or -not (Test-Path -LiteralPath $targetExecutable -PathType Leaf)
    if (-not $copySource) { $copySource = (Get-FirefoxRuntimeVersion -Executable $targetExecutable) -lt $sourceVersion }
    if ($copySource) {
        # Mark our reserved destination before copying, allowing a failed copy
        # to be completed on retry without touching an unrelated installation.
        @{ Owner='WhiteSur-Monterey-Adaptive-Windows'; Source=$sourceDirectory; Ready=$false } |
            ConvertTo-Json | Set-Content -LiteralPath $markerPath -Encoding UTF8
        & robocopy $sourceDirectory $destination /E /R:1 /W:1 /NFL /NDL /NJH /NJS /NP /XD tobedeleted updates | Out-Host
        if ($LASTEXITCODE -ge 8) { throw "Firefox could not be copied (robocopy exit $LASTEXITCODE)." }
    }
    foreach ($relative in @('whitesur.cfg', 'defaults\pref\whitesur-autoconfig.js')) {
        $sourceFile = Join-Path (Join-Path $PackageRoot 'firefox') $relative
        $targetFile = Join-Path $destination $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $targetFile) -Force | Out-Null
        [IO.File]::WriteAllText($targetFile, [IO.File]::ReadAllText($sourceFile).Replace("`r`n", "`n"), [Text.UTF8Encoding]::new($false))
    }
    @{ Owner='WhiteSur-Monterey-Adaptive-Windows'; Source=$sourceDirectory; Ready=$true;
       Version=(Get-FirefoxRuntimeVersion -Executable $targetExecutable).ToString() } |
        ConvertTo-Json | Set-Content -LiteralPath $markerPath -Encoding UTF8
    return [pscustomobject]@{ Enabled=$true; InPlace=$false; Executable=$targetExecutable; Reason='Editable tabs enabled in the explicitly requested separate Firefox installation.' }
}

function Remove-EditableTabsLauncher {
    param([string]$ProfileDirectory)
    $statePath = Get-EditableTabsStatePath -ProfileDirectory $ProfileDirectory
    if (-not (Test-Path -LiteralPath $statePath -PathType Leaf)) { return }
    $state = Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
    if ($state.Owner -ne 'WhiteSur-Monterey-Adaptive-Windows') { throw 'The editable-tabs profile ownership marker is invalid.' }
    if ($state.Shortcut -and (Test-Path -LiteralPath $state.Shortcut -PathType Leaf)) {
        $shell = New-Object -ComObject WScript.Shell
        $link = $shell.CreateShortcut($state.Shortcut)
        if ((Test-PathEquals -Left $link.TargetPath -Right $state.Executable) -and
            $link.Arguments -eq $state.Arguments) {
            Remove-Item -LiteralPath $state.Shortcut -Force
        } else { Write-Status 'The launcher was modified after installation and was left untouched.' Yellow }
    }
    Remove-Item -LiteralPath $statePath -Force
}

function Set-EditableTabsLauncher {
    param([pscustomobject]$Profile, [pscustomobject]$Runtime, [string]$ShortcutDirectory)
    Remove-EditableTabsLauncher -ProfileDirectory $Profile.Path
    if (-not $Runtime.Enabled) { return }
    if ($Runtime.InPlace) {
        @{ Owner='WhiteSur-Monterey-Adaptive-Windows'; Executable=$Runtime.Executable;
           Shortcut=$null; Arguments=('-no-remote -profile "' + $Profile.Path + '"') } | ConvertTo-Json |
            Set-Content -LiteralPath (Get-EditableTabsStatePath -ProfileDirectory $Profile.Path) -Encoding UTF8
        Write-Status 'Your existing Firefox is configured; open it using your usual shortcut.' Green
        return
    }
    if ([string]::IsNullOrWhiteSpace($ShortcutDirectory)) {
        $ShortcutDirectory = [Environment]::GetFolderPath([Environment+SpecialFolder]::DesktopDirectory)
    }
    New-Item -ItemType Directory -Path $ShortcutDirectory -Force | Out-Null
    $safeName = (Split-Path -Leaf $Profile.Path) -replace '[<>:"/\\|?*]', '_'
    $shortcut = Join-Path $ShortcutDirectory "WhiteSur Firefox - $safeName.lnk"
    if (Test-Path -LiteralPath $shortcut) { throw "A launcher already exists at $shortcut; it was not overwritten." }
    $arguments = '-no-remote -profile "' + $Profile.Path + '"'
    $shell = New-Object -ComObject WScript.Shell
    $link = $shell.CreateShortcut($shortcut)
    $link.TargetPath = $Runtime.Executable
    $link.Arguments = $arguments
    $link.WorkingDirectory = Split-Path -Parent $Runtime.Executable
    $link.IconLocation = $Runtime.Executable + ',0'
    $link.Description = 'WhiteSur adaptive Firefox with editable tabs.'
    $link.Save()
    @{ Owner='WhiteSur-Monterey-Adaptive-Windows'; Executable=$Runtime.Executable;
       Shortcut=$shortcut; Arguments=$arguments } | ConvertTo-Json |
        Set-Content -LiteralPath (Get-EditableTabsStatePath -ProfileDirectory $Profile.Path) -Encoding UTF8
    Write-Status "Start Firefox using '$shortcut'." Green
}

function Assert-ProfileChromePath {
    param([string]$ProfileDirectory)
    # .NET expands existing 8.3 segments (e.g. RUNNER~1) when normalizing the
    # chrome path. Normalize its parent the same way before comparing them.
    $profileRoot = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath $ProfileDirectory).ProviderPath).TrimEnd('\')
    $chromePath = [IO.Path]::GetFullPath((Join-Path $profileRoot 'chrome'))
    if (-not (Test-PathEquals -Left (Split-Path -Parent $chromePath) -Right $profileRoot)) {
        throw 'The chrome directory is outside the selected profile.'
    }
    if ((Test-Path -LiteralPath $chromePath) -and
        ((Get-Item -LiteralPath $chromePath).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw 'The profile chrome directory is a junction or symbolic link; it was left untouched.'
    }
}
