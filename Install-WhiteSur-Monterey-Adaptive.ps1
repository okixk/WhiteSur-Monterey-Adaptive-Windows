#requires -Version 5.1
<#
.SYNOPSIS
Installs WhiteSur Monterey Adaptive into the active Firefox profile on Windows 10/11.

.DESCRIPTION
Finds the profile selected by Firefox's Install section, backs up an existing
chrome directory, copies the Windows-compatible Monterey Adaptive package, and
manages the required Firefox user preferences in user.js.
#>
[CmdletBinding()]
param(
    [Parameter()]
    [ValidateNotNullOrEmpty()]
    [string]$ProfilePath,

    [Parameter()]
    [switch]$AllProfiles,

    [Parameter()]
    [switch]$Uninstall,

    [Parameter()]
    [switch]$Diagnose,

    [Parameter()]
    [switch]$Force,

    [Parameter()]
    [switch]$NoBackup
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$PackageRoot = Split-Path -Parent $PSCommandPath
$ChromeSource = Join-Path $PackageRoot 'chrome'
$ThemeMarkerName = '.whitesur-monterey-adaptive-windows'
$PreferenceBegin = '// BEGIN WhiteSur Monterey Adaptive Windows'
$PreferenceEnd = '// END WhiteSur Monterey Adaptive Windows'

function Write-Status {
    param(
        [Parameter(Mandatory)]
        [string]$Message,

        [Parameter()]
        [ConsoleColor]$Color = [ConsoleColor]::Cyan
    )

    Write-Host "[WhiteSur] $Message" -ForegroundColor $Color
}

function Get-FirefoxRoot {
    $appData = [Environment]::GetFolderPath([Environment+SpecialFolder]::ApplicationData)
    if ([string]::IsNullOrWhiteSpace($appData)) {
        throw 'The Windows roaming AppData directory could not be determined.'
    }

    return (Join-Path $appData 'Mozilla\Firefox')
}

function Read-IniFile {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    $sections = [ordered]@{}
    $currentName = $null

    foreach ($rawLine in Get-Content -LiteralPath $Path -ErrorAction Stop) {
        $line = $rawLine.Trim()

        if ([string]::IsNullOrWhiteSpace($line) -or $line.StartsWith(';') -or $line.StartsWith('#')) {
            continue
        }

        if ($line -match '^\[(.+)\]$') {
            $currentName = $Matches[1]
            if (-not $sections.Contains($currentName)) {
                $sections[$currentName] = [ordered]@{}
            }
            continue
        }

        if (($null -ne $currentName) -and ($line -match '^([^=]+)=(.*)$')) {
            $sections[$currentName][$Matches[1].Trim()] = $Matches[2].Trim()
        }
    }

    return ,$sections
}

function Get-NormalizedFirefoxPath {
    param(
        [Parameter(Mandatory)]
        [string]$FirefoxRoot,

        [Parameter(Mandatory)]
        [string]$RawPath
    )

    $normalized = $RawPath.Replace('/', [System.IO.Path]::DirectorySeparatorChar)
    $candidate = if ([System.IO.Path]::IsPathRooted($normalized)) {
        $normalized
    }
    else {
        Join-Path $FirefoxRoot $normalized
    }

    if (Test-Path -LiteralPath $candidate -PathType Container) {
        return (Resolve-Path -LiteralPath $candidate).Path
    }

    return [System.IO.Path]::GetFullPath($candidate)
}

function Test-PathEquals {
    param(
        [Parameter(Mandatory)]
        [string]$Left,

        [Parameter(Mandatory)]
        [string]$Right
    )

    return [string]::Equals(
        $Left.TrimEnd('\', '/'),
        $Right.TrimEnd('\', '/'),
        [System.StringComparison]::OrdinalIgnoreCase
    )
}

function Get-ProfileLastUsedTime {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )

    foreach ($fileName in @('prefs.js', 'sessionstore.jsonlz4', 'times.json')) {
        $candidate = Join-Path $Path $fileName
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return (Get-Item -LiteralPath $candidate).LastWriteTime
        }
    }

    return (Get-Item -LiteralPath $Path).LastWriteTime
}

function Get-FirefoxProfiles {
    $firefoxRoot = Get-FirefoxRoot
    $profilesIni = Join-Path $firefoxRoot 'profiles.ini'
    $installsIni = Join-Path $firefoxRoot 'installs.ini'
    $results = [System.Collections.Generic.List[object]]::new()
    $installDefaultPaths = [System.Collections.Generic.List[string]]::new()

    foreach ($iniPath in @($profilesIni, $installsIni)) {
        if (-not (Test-Path -LiteralPath $iniPath -PathType Leaf)) {
            continue
        }

        $ini = Read-IniFile -Path $iniPath
        foreach ($sectionName in $ini.Keys) {
            $section = $ini[$sectionName]
            $isInstallSection = ($sectionName -like 'Install*') -or ([System.IO.Path]::GetFileName($iniPath) -ieq 'installs.ini')
            if ($isInstallSection -and $section.Contains('Default')) {
                $resolvedDefault = Get-NormalizedFirefoxPath -FirefoxRoot $firefoxRoot -RawPath ([string]$section['Default'])
                if (-not ($installDefaultPaths | Where-Object { Test-PathEquals -Left $_ -Right $resolvedDefault })) {
                    $installDefaultPaths.Add($resolvedDefault)
                }
            }
        }
    }

    if (Test-Path -LiteralPath $profilesIni -PathType Leaf) {
        $profilesData = Read-IniFile -Path $profilesIni
        foreach ($sectionName in $profilesData.Keys) {
            if ($sectionName -notmatch '^Profile\d+$') {
                continue
            }

            $section = $profilesData[$sectionName]
            if (-not $section.Contains('Path')) {
                continue
            }

            $isRelative = (-not $section.Contains('IsRelative')) -or ([string]$section['IsRelative'] -eq '1')
            $candidate = if ($isRelative) {
                Get-NormalizedFirefoxPath -FirefoxRoot $firefoxRoot -RawPath ([string]$section['Path'])
            }
            else {
                [System.IO.Path]::GetFullPath([string]$section['Path'])
            }

            if (-not (Test-Path -LiteralPath $candidate -PathType Container)) {
                continue
            }

            $resolved = (Resolve-Path -LiteralPath $candidate).Path
            $isInstallDefault = [bool]($installDefaultPaths | Where-Object { Test-PathEquals -Left $_ -Right $resolved })
            $results.Add([pscustomobject]@{
                Name = if ($section.Contains('Name')) { [string]$section['Name'] } else { $sectionName }
                Path = $resolved
                InstallDefault = $isInstallDefault
                ProfileDefault = $section.Contains('Default') -and ([string]$section['Default'] -eq '1')
                LastUsedTime = Get-ProfileLastUsedTime -Path $resolved
            })
        }
    }

    foreach ($installDefaultPath in $installDefaultPaths) {
        if (-not (Test-Path -LiteralPath $installDefaultPath -PathType Container)) {
            continue
        }

        $alreadyListed = [bool]($results | Where-Object { Test-PathEquals -Left $_.Path -Right $installDefaultPath })
        if (-not $alreadyListed) {
            $resolved = (Resolve-Path -LiteralPath $installDefaultPath).Path
            $results.Add([pscustomobject]@{
                Name = Split-Path -Leaf $resolved
                Path = $resolved
                InstallDefault = $true
                ProfileDefault = $false
                LastUsedTime = Get-ProfileLastUsedTime -Path $resolved
            })
        }
    }

    if ($results.Count -eq 0) {
        $profilesDirectory = Join-Path $firefoxRoot 'Profiles'
        if (Test-Path -LiteralPath $profilesDirectory -PathType Container) {
            foreach ($directory in Get-ChildItem -LiteralPath $profilesDirectory -Directory -ErrorAction Stop) {
                $results.Add([pscustomobject]@{
                    Name = $directory.Name
                    Path = $directory.FullName
                    InstallDefault = $false
                    ProfileDefault = $false
                    LastUsedTime = Get-ProfileLastUsedTime -Path $directory.FullName
                })
            }
        }
    }

    return $results
}

function Get-SelectedProfiles {
    if (-not [string]::IsNullOrWhiteSpace($ProfilePath)) {
        if (-not (Test-Path -LiteralPath $ProfilePath -PathType Container)) {
            throw "Firefox profile directory does not exist: $ProfilePath"
        }

        $resolved = (Resolve-Path -LiteralPath $ProfilePath).Path
        return @([pscustomobject]@{
            Name = Split-Path -Leaf $resolved
            Path = $resolved
            InstallDefault = $true
            ProfileDefault = $true
            LastUsedTime = Get-ProfileLastUsedTime -Path $resolved
        })
    }

    $profiles = @(Get-FirefoxProfiles)
    if ($profiles.Count -eq 0) {
        throw 'No Firefox profile was found. Start Firefox once, close it, and run this installer again.'
    }

    if ($AllProfiles) {
        return @($profiles | Sort-Object Name)
    }

    $installDefaults = @($profiles | Where-Object InstallDefault | Sort-Object LastUsedTime -Descending)
    if ($installDefaults.Count -gt 0) {
        return @($installDefaults[0])
    }

    $profileDefaults = @($profiles | Where-Object ProfileDefault | Sort-Object LastUsedTime -Descending)
    if ($profileDefaults.Count -gt 0) {
        return @($profileDefaults[0])
    }

    return @($profiles | Sort-Object LastUsedTime -Descending | Select-Object -First 1)
}

function Remove-ManagedPreferenceBlock {
    param(
        [Parameter()]
        [AllowNull()]
        [AllowEmptyString()]
        [string]$Text = ''
    )

    if ([string]::IsNullOrEmpty($Text)) {
        return ''
    }

    $escapedBegin = [regex]::Escape($PreferenceBegin)
    $escapedEnd = [regex]::Escape($PreferenceEnd)
    $pattern = "(?ms)^\s*$escapedBegin\s*\r?\n.*?^\s*$escapedEnd\s*\r?\n?"
    return [regex]::Replace($Text, $pattern, '')
}

function Set-ManagedPreferences {
    param(
        [Parameter(Mandatory)]
        [string]$FirefoxProfilePath,

        [Parameter(Mandatory)]
        [bool]$Enabled
    )

    $userJs = Join-Path $FirefoxProfilePath 'user.js'
    $rawExisting = if (Test-Path -LiteralPath $userJs -PathType Leaf) {
        Get-Content -LiteralPath $userJs -Raw -ErrorAction Stop
    }
    else {
        $null
    }

    $existing = if ($null -eq $rawExisting) { '' } else { [string]$rawExisting }
    $clean = [string](Remove-ManagedPreferenceBlock -Text $existing)
    $clean = $clean.TrimEnd()

    if ($Enabled) {
        $block = @"
$PreferenceBegin
user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);
user_pref("browser.tabs.drawInTitlebar", true);
user_pref("browser.uidensity", 0);
user_pref("svg.context-properties.content.enabled", true);
$PreferenceEnd
"@

        if ([string]::IsNullOrWhiteSpace($clean)) {
            $updated = $block.TrimStart()
        }
        else {
            $updated = "$clean`r`n`r`n$($block.TrimStart())"
        }
    }
    else {
        $updated = $clean
        if (-not [string]::IsNullOrWhiteSpace($updated)) {
            $updated += "`r`n"
        }
    }

    [System.IO.File]::WriteAllText($userJs, $updated, [System.Text.UTF8Encoding]::new($false))
}

function Get-ProfileStatus {
    param(
        [Parameter(Mandatory)]
        [pscustomobject]$Profile
    )

    $chrome = Join-Path $Profile.Path 'chrome'
    $userChrome = Join-Path $chrome 'userChrome.css'
    $marker = Join-Path $chrome $ThemeMarkerName
    $userJs = Join-Path $Profile.Path 'user.js'
    $prefEnabled = $false

    if (Test-Path -LiteralPath $userJs -PathType Leaf) {
        $userJsText = Get-Content -LiteralPath $userJs -Raw -ErrorAction SilentlyContinue
        $prefEnabled = $null -ne $userJsText -and $userJsText -match 'toolkit\.legacyUserProfileCustomizations\.stylesheets"\s*,\s*true'
    }

    return [pscustomobject]@{
        Name = $Profile.Name
        Path = $Profile.Path
        InstallDefault = $Profile.InstallDefault
        ProfileDefault = $Profile.ProfileDefault
        LastUsed = $Profile.LastUsedTime
        ChromeFolder = Test-Path -LiteralPath $chrome -PathType Container
        UserChromeCss = Test-Path -LiteralPath $userChrome -PathType Leaf
        WhiteSurMarker = Test-Path -LiteralPath $marker -PathType Leaf
        PreferenceInUserJs = $prefEnabled
    }
}

function Show-Diagnostics {
    $profiles = if (-not [string]::IsNullOrWhiteSpace($ProfilePath)) {
        @(Get-SelectedProfiles)
    }
    else {
        @(Get-FirefoxProfiles | Sort-Object InstallDefault, ProfileDefault, LastUsedTime -Descending)
    }

    Write-Host ''
    Write-Status 'Detected Firefox profiles:' White
    foreach ($profile in $profiles) {
        $status = Get-ProfileStatus -Profile $profile
        Write-Host ''
        Write-Host "  Name:               $($status.Name)"
        Write-Host "  Path:               $($status.Path)"
        Write-Host "  Firefox install default: $($status.InstallDefault)"
        Write-Host "  Legacy profile default:  $($status.ProfileDefault)"
        Write-Host "  Last used:          $($status.LastUsed)"
        Write-Host "  chrome folder:      $($status.ChromeFolder)"
        Write-Host "  userChrome.css:     $($status.UserChromeCss)"
        Write-Host "  WhiteSur marker:    $($status.WhiteSurMarker)"
        Write-Host "  user.js preference: $($status.PreferenceInUserJs)"
    }

    Write-Host ''
    $selected = @(Get-SelectedProfiles)
    foreach ($profile in $selected) {
        Write-Status "Installer would use: $($profile.Path)" Green
    }
}

function Install-ThemeForProfile {
    param(
        [Parameter(Mandatory)]
        [pscustomobject]$Profile
    )

    $targetChrome = Join-Path $Profile.Path 'chrome'
    $marker = Join-Path $targetChrome $ThemeMarkerName
    $preservedCustomChrome = $null

    $selectionLabel = if ($Profile.InstallDefault) { 'Firefox install default' } elseif ($Profile.ProfileDefault) { 'legacy profile default' } else { 'most recently used profile' }
    Write-Status "Installing into '$($Profile.Name)' ($selectionLabel): $($Profile.Path)"

    if (Test-Path -LiteralPath $targetChrome -PathType Container) {
        if (Test-Path -LiteralPath $marker -PathType Leaf) {
            $customChrome = Join-Path $targetChrome 'customChrome.css'
            if (Test-Path -LiteralPath $customChrome -PathType Leaf) {
                $preservedCustomChrome = [System.IO.Path]::GetTempFileName()
                Copy-Item -LiteralPath $customChrome -Destination $preservedCustomChrome -Force
            }

            Remove-Item -LiteralPath $targetChrome -Recurse -Force
        }
        elseif ($NoBackup) {
            Write-Status 'Removing the existing chrome directory because -NoBackup was supplied.' Yellow
            Remove-Item -LiteralPath $targetChrome -Recurse -Force
        }
        else {
            $timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
            $backup = Join-Path $Profile.Path "chrome.whitesur-backup-$timestamp"
            Move-Item -LiteralPath $targetChrome -Destination $backup
            Write-Status "Existing chrome directory backed up to '$backup'." DarkGray
        }
    }

    Copy-Item -LiteralPath $ChromeSource -Destination $targetChrome -Recurse -Force

    if (($null -ne $preservedCustomChrome) -and (Test-Path -LiteralPath $preservedCustomChrome)) {
        Copy-Item -LiteralPath $preservedCustomChrome -Destination (Join-Path $targetChrome 'customChrome.css') -Force
        Remove-Item -LiteralPath $preservedCustomChrome -Force
    }

    @(
        'WhiteSur Monterey Adaptive for Windows'
        "Installed: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')"
        "Package: $PackageRoot"
        "Profile: $($Profile.Path)"
    ) | Set-Content -LiteralPath $marker -Encoding UTF8

    Set-ManagedPreferences -FirefoxProfilePath $Profile.Path -Enabled $true

    $status = Get-ProfileStatus -Profile $Profile
    if (-not ($status.UserChromeCss -and $status.WhiteSurMarker -and $status.PreferenceInUserJs)) {
        throw "Post-install verification failed for '$($Profile.Path)'."
    }

    Write-Status "Verified '$($Profile.Name)': userChrome.css and required preference are present." Green
}

function Uninstall-ThemeForProfile {
    param(
        [Parameter(Mandatory)]
        [pscustomobject]$Profile
    )

    $targetChrome = Join-Path $Profile.Path 'chrome'
    $marker = Join-Path $targetChrome $ThemeMarkerName

    Write-Status "Removing from '$($Profile.Name)' ($($Profile.Path))"
    Set-ManagedPreferences -FirefoxProfilePath $Profile.Path -Enabled $false

    if (Test-Path -LiteralPath $marker -PathType Leaf) {
        Remove-Item -LiteralPath $targetChrome -Recurse -Force
    }
    elseif (Test-Path -LiteralPath $targetChrome -PathType Container) {
        Write-Status 'The current chrome directory was not created by this installer, so it was left untouched.' Yellow
        return
    }

    $backup = Get-ChildItem -LiteralPath $Profile.Path -Directory -Filter 'chrome.whitesur-backup-*' -ErrorAction SilentlyContinue |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if ($null -ne $backup) {
        Move-Item -LiteralPath $backup.FullName -Destination $targetChrome
        Write-Status "Restored '$($backup.Name)' as the active chrome directory." Green
    }
    else {
        Write-Status 'Theme removed; there was no earlier chrome directory to restore.' Green
    }
}

if ($Diagnose) {
    Show-Diagnostics
    exit 0
}

if (-not $Uninstall -and -not (Test-Path -LiteralPath $ChromeSource -PathType Container)) {
    throw "The package chrome directory is missing: $ChromeSource"
}

$runningFirefox = @(Get-Process -Name firefox -ErrorAction SilentlyContinue)
if (($runningFirefox.Count -gt 0) -and -not $Force) {
    throw 'Firefox is running. Close every Firefox window and run the installer again. Use -Force only when you understand the risk.'
}

$selectedProfiles = @(Get-SelectedProfiles)
foreach ($profile in $selectedProfiles) {
    if ($Uninstall) {
        Uninstall-ThemeForProfile -Profile $profile
    }
    else {
        Install-ThemeForProfile -Profile $profile
    }
}

if ($Uninstall) {
    Write-Status 'Uninstallation complete. Start Firefox again.' Green
}
else {
    Write-Status 'Installation complete. Start Firefox again. Adaptive Tab Bar Colour is only needed for website-based colours.' Green
}
