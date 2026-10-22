#requires -Version 5.1
$ErrorActionPreference = 'Stop'
$repository = Split-Path -Parent $PSScriptRoot
$installer = Join-Path $repository 'Install-WhiteSur-Monterey-Adaptive.ps1'
$temporaryBase = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\')
$testRoot = Join-Path $temporaryBase ('whitesur-installer-tests-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testRoot | Out-Null
$checks = 0
function Check([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw "FAIL: $Message" }
    $script:checks++
    Write-Host "PASS: $Message"
}
function Fake-Firefox([string]$Name, [string]$Version) {
    $path = Join-Path $testRoot $Name
    New-Item -ItemType Directory -Path (Join-Path $path 'defaults\pref') -Force | Out-Null
    [IO.File]::WriteAllText((Join-Path $path 'firefox.exe'), 'installer fixture; never executed')
    [IO.File]::WriteAllText((Join-Path $path 'application.ini'), "[App]`nVersion=$Version`n")
    return (Join-Path $path 'firefox.exe')
}
function Profile([string]$Name) {
    $path = Join-Path $testRoot $Name
    New-Item -ItemType Directory -Path $path | Out-Null
    [IO.File]::WriteAllText((Join-Path $path 'user.js'), 'user_pref("unrelated.preference", true);')
    return $path
}
function Install([string]$Path, [hashtable]$Extra = @{}) {
    & $installer -ProfilePath $Path -FirefoxPath $script:modern -RuntimeDirectory $script:runtime -ShortcutDirectory $script:shortcuts -Force @Extra
    if ($LASTEXITCODE -ne 0) { throw "Installer returned $LASTEXITCODE" }
}
try {
    $modern = Fake-Firefox 'source-modern' '158.0.1'
    $runtime = Join-Path $testRoot 'runtime'
    $shortcuts = Join-Path $testRoot 'shortcuts'
    $first = Profile 'first.default-release'
    New-Item -ItemType Directory -Path (Join-Path $first 'chrome') | Out-Null
    [IO.File]::WriteAllText((Join-Path $first 'chrome\original.css'), 'original theme')
    Install $first
    $state = Get-Content (Join-Path $first '.whitesur-editable-tabs.json') -Raw | ConvertFrom-Json
    Check (Test-Path -LiteralPath $state.Shortcut) 'explicit separate runtime creates a profile-specific launcher'
    Check ($state.Executable -eq (Join-Path $runtime 'firefox.exe')) 'launcher uses the isolated Firefox copy'
    Check ([IO.File]::ReadAllText((Join-Path $first 'user.js')).Contains('user_pref("userChrome.tabSearch.enabled", true);')) 'editable tabs are enabled by default'
    Check (Test-Path -LiteralPath (Join-Path $first 'chrome\tab-search.uc.js')) 'profile contains the runtime script'
    $prefBytes = [IO.File]::ReadAllBytes((Join-Path $runtime 'defaults\pref\whitesur-autoconfig.js'))
    Check (-not ($prefBytes -contains 13) -and $prefBytes[0] -eq 112) 'AutoConfig preferences use LF and UTF-8 without BOM'
    Check ([IO.File]::ReadAllText((Join-Path $runtime 'whitesur.cfg')).StartsWith('//')) 'AutoConfig starts with the required comment'

    # Capture the process launch without executing the fake browser fixture.
    $launchCapture = [pscustomobject]@{ Executable=$null; Arguments=$null }
    function Start-Process {
        param([string]$FilePath, [string]$ArgumentList)
        $launchCapture.Executable = $FilePath
        $launchCapture.Arguments = $ArgumentList
    }
    try {
        Install $first @{Launch=$true}
        Check ($launchCapture.Executable -eq $state.Executable) 'automatic launch uses the Firefox copy containing the loader'
        Check ($launchCapture.Arguments -eq $state.Arguments) 'automatic launch explicitly uses the installed profile'
    } finally {
        Remove-Item Function:\Start-Process
    }

    [IO.File]::WriteAllText((Join-Path $first 'chrome\customChrome.css'), '/* keep my overrides */')
    Install $first
    Check ([IO.File]::ReadAllText((Join-Path $first 'chrome\customChrome.css')) -eq '/* keep my overrides */') 'update preserves customChrome.css'
    $prefs = [IO.File]::ReadAllText((Join-Path $first 'user.js'))
    Check ([regex]::Matches($prefs, '// BEGIN WhiteSur Monterey Adaptive Windows').Count -eq 1) 'update keeps one managed preference block'
    Check (@(Get-ChildItem -LiteralPath $first -Directory -Filter 'chrome.whitesur-backup-*').Count -eq 1) 'update retains the original theme backup'
    $newer = Fake-Firefox 'source-newer' '159.0.1'
    & $installer -ProfilePath $first -FirefoxPath $newer -RuntimeDirectory $runtime -ShortcutDirectory $shortcuts -Force
    Check ([IO.File]::ReadAllText((Join-Path $runtime 'application.ini')).Contains('159.0.1')) 'update refreshes an older binary copy'
    Install $first
    Check ([IO.File]::ReadAllText((Join-Path $runtime 'application.ini')).Contains('159.0.1')) 'update does not downgrade a newer binary copy'
    & $installer -ProfilePath $first -FirefoxPath (Join-Path $runtime 'firefox.exe') -RuntimeDirectory $runtime -ShortcutDirectory $shortcuts -Force
    Check (Test-Path -LiteralPath (Join-Path $first '.whitesur-editable-tabs.json')) 'a completed owned runtime can be reused as the source'
    Add-Type -TypeDefinition @'
using System.Text;
using System.Runtime.InteropServices;
public static class WhiteSurInstallerTestPaths {
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern uint GetShortPathName(string longPath, StringBuilder buffer, uint size);
}
'@
    $shortBuffer = [Text.StringBuilder]::new(4096)
    if ([WhiteSurInstallerTestPaths]::GetShortPathName($first, $shortBuffer, 4096) -eq 0) {
        throw 'Could not resolve the installer short-path fixture.'
    }
    Install $shortBuffer.ToString()
    Check (Test-Path -LiteralPath (Join-Path $first '.whitesur-editable-tabs.json')) 'profile paths accept Windows 8.3 aliases without weakening the chrome guard'
    $state = Get-Content (Join-Path $first '.whitesur-editable-tabs.json') -Raw | ConvertFrom-Json
    & $installer -ProfilePath $first -Diagnose
    Check ($LASTEXITCODE -eq 0) 'diagnostics work for editable-tabs installations'

    $second = Profile 'second.private'
    Install $second
    $secondState = Get-Content (Join-Path $second '.whitesur-editable-tabs.json') -Raw | ConvertFrom-Json
    Install $first @{ClassicToolbar=$true}
    Check (-not (Test-Path -LiteralPath $state.Shortcut)) 'switching to classic mode removes only its own launcher'
    Check (Test-Path -LiteralPath $secondState.Shortcut) 'another profile launcher is preserved'
    Check ([IO.File]::ReadAllText((Join-Path $first 'user.js')).Contains('user_pref("userChrome.tabSearch.enabled", false);')) 'classic mode explicitly disables the script'
    & $installer -ProfilePath $first -Uninstall -Force
    Check ([IO.File]::ReadAllText((Join-Path $first 'chrome\original.css')) -eq 'original theme') 'uninstall restores the original chrome directory'
    $cleanPrefs = [IO.File]::ReadAllText((Join-Path $first 'user.js'))
    Check ($cleanPrefs.Contains('unrelated.preference') -and -not $cleanPrefs.Contains('userChrome.tabSearch')) 'uninstall preserves unrelated preferences'

    $shell = New-Object -ComObject WScript.Shell
    $modified = $shell.CreateShortcut($secondState.Shortcut)
    $modified.TargetPath = Join-Path $env:WINDIR 'notepad.exe'
    $modified.Arguments = ''
    $modified.Save()
    & $installer -ProfilePath $second -Uninstall -Force
    Check (Test-Path -LiteralPath $secondState.Shortcut) 'uninstall preserves a launcher repurposed by the user'
    Check (Test-Path -LiteralPath (Join-Path $runtime 'firefox.exe')) 'uninstall retains the shared Firefox copy'

    $old = Fake-Firefox 'source-old' '156.0'
    $olderProfile = Profile 'older'
    $oldFailed = $false
    try {
        & $installer -ProfilePath $olderProfile -FirefoxPath $old -RuntimeDirectory (Join-Path $testRoot 'old-runtime') -ShortcutDirectory $shortcuts -Force
    } catch { $oldFailed = $_.Exception.Message -match 'Firefox 158\+' }
    Check $oldFailed 'unsupported Firefox reports that editable tabs could not be installed'
    Check (-not (Test-Path -LiteralPath (Join-Path $olderProfile 'chrome'))) 'unsupported Firefox does not replace the profile theme'
    $cmdProfile = Profile 'cmd profile with spaces'
    $cmdStart = New-Object System.Diagnostics.ProcessStartInfo
    $cmdStart.FileName = $env:ComSpec
    $cmdStart.Arguments = '/d /c ""' + (Join-Path $repository 'Install.cmd') + '" -ProfilePath "' + $cmdProfile + '" -FirefoxPath "' + $old + '" -Force"'
    $cmdStart.UseShellExecute = $false
    $cmdStart.CreateNoWindow = $true
    $cmdStart.RedirectStandardInput = $true
    $cmdStart.RedirectStandardOutput = $true
    $cmdStart.RedirectStandardError = $true
    $cmdProcess = [Diagnostics.Process]::Start($cmdStart)
    try {
        $cmdProcess.StandardInput.WriteLine()
        $cmdProcess.StandardInput.Close()
        $cmdOutput = $cmdProcess.StandardOutput.ReadToEnd() + $cmdProcess.StandardError.ReadToEnd()
        $cmdProcess.WaitForExit()
        Check ($cmdProcess.ExitCode -ne 0) 'Install.cmd propagates editable-tab setup failure as a nonzero exit code'
        Check ($cmdOutput -match 'Firefox 158\+') 'Install.cmd forwards quoted Firefox and profile paths to the installer'
        Check (-not (Test-Path -LiteralPath (Join-Path $cmdProfile 'chrome'))) 'failed CMD installation leaves the selected profile untouched'
    } finally {
        $cmdProcess.Dispose()
    }
    & $installer -ProfilePath $olderProfile -FirefoxPath $old -ClassicToolbar -Force
    Check ([IO.File]::ReadAllText((Join-Path $olderProfile 'user.js')).Contains('tabSearch.enabled", false')) 'older Firefox supports explicitly selected classic mode'

    $conflicting = Fake-Firefox 'source-configured' '158.0.1'
    $foreignPref = Join-Path (Split-Path -Parent $conflicting) 'defaults\pref\corporate.js'
    $foreignText = 'pref("general.config.filename", "corporate.cfg");'
    [IO.File]::WriteAllText($foreignPref, $foreignText)
    $configuredProfile = Profile 'configured'
    $configFailed = $false
    try {
        & $installer -ProfilePath $configuredProfile -FirefoxPath $conflicting -RuntimeDirectory (Join-Path $testRoot 'foreign-runtime') -Force
    } catch { $configFailed = $_.Exception.Message -match 'AutoConfig' }
    Check $configFailed 'AutoConfig conflicts report a failed editable-tabs installation'
    Check ([IO.File]::ReadAllText($foreignPref) -eq $foreignText) 'existing AutoConfig remains untouched'
    Check (-not (Test-Path -LiteralPath (Join-Path $configuredProfile 'chrome'))) 'AutoConfig conflicts leave the profile theme untouched'

    $unmanaged = Join-Path $testRoot 'unmanaged-runtime'
    New-Item -ItemType Directory -Path $unmanaged | Out-Null
    [IO.File]::WriteAllText((Join-Path $unmanaged 'sentinel.txt'), 'keep me')
    $guardedProfile = Profile 'guarded'
    $runtimeFailed = $false
    try {
        & $installer -ProfilePath $guardedProfile -FirefoxPath $modern -RuntimeDirectory $unmanaged -Force
    } catch { $runtimeFailed = $_.Exception.Message -match 'unmanaged directory' }
    Check $runtimeFailed 'runtime setup errors fail instead of reporting a successful CSS installation'
    Check (-not (Test-Path -LiteralPath (Join-Path $guardedProfile 'chrome'))) 'runtime setup errors leave the profile theme untouched'
    Check ([IO.File]::ReadAllText((Join-Path $unmanaged 'sentinel.txt')) -eq 'keep me') 'unmanaged runtime directories are preserved'
    Check (-not (Test-Path -LiteralPath (Join-Path $unmanaged 'firefox.exe'))) 'failed runtime setup cannot overwrite an unrelated directory'

    $existing = Fake-Firefox 'existing Firefox' '158.0.1'
    $existingDirectory = Split-Path -Parent $existing
    $existingProfile = Profile 'existing profile'
    $existingHash = (Get-FileHash -LiteralPath $existing).Hash
    $shortcutCount = @(Get-ChildItem -LiteralPath $shortcuts -Filter '*.lnk').Count
    & $installer -ProfilePath $existingProfile -FirefoxPath $existing -ShortcutDirectory $shortcuts -Force
    $existingState = Get-Content (Join-Path $existingProfile '.whitesur-editable-tabs.json') -Raw | ConvertFrom-Json
    Check ($existingState.Executable -eq $existing) 'default installation configures the existing Firefox executable'
    Check ((Get-FileHash -LiteralPath $existing).Hash -eq $existingHash) 'default installation preserves the original Firefox binary'
    Check (-not $existingState.Shortcut -and @(Get-ChildItem -LiteralPath $shortcuts -Filter '*.lnk').Count -eq $shortcutCount) 'default installation creates no additional Firefox shortcut'
    Check (Test-Path -LiteralPath (Join-Path $existingDirectory 'whitesur.cfg')) 'the existing Firefox installation receives the loader'
    Check (Test-Path -LiteralPath (Join-Path $existingDirectory 'defaults\pref\whitesur-autoconfig.js')) 'the existing Firefox installation enables AutoConfig'
    Check (-not (Test-Path -LiteralPath (Join-Path $existingDirectory '.whitesur-runtime.json'))) 'default installation does not create a managed Firefox copy'
    & $installer -ProfilePath $existingProfile -FirefoxPath $existing -Force
    Check ($LASTEXITCODE -eq 0) 'updating the existing Firefox loader is supported'
    & $installer -ProfilePath $existingProfile -Diagnose
    Check ($LASTEXITCODE -eq 0) 'diagnostics accept an existing Firefox installation without a new launcher'
    & $installer -ProfilePath $existingProfile -Uninstall -Force
    Check ((Test-Path -LiteralPath $existing) -and -not (Test-Path -LiteralPath (Join-Path $existingProfile 'chrome'))) 'uninstall removes the profile theme and preserves existing Firefox'

    $helperFirefox = Fake-Firefox 'helper Firefox' '158.0.1'
    & (Join-Path $repository 'Install-Editable-Tabs-Loader.ps1') -FirefoxDirectory (Split-Path -Parent $helperFirefox)
    Check ($LASTEXITCODE -eq 0 -and (Test-Path -LiteralPath (Join-Path (Split-Path -Parent $helperFirefox) 'whitesur.cfg'))) 'the elevation helper installs loader files without running profile installation'

    # Simulate a protected installation without opening a UAC dialog in tests.
    $PackageRoot = $repository
    . (Join-Path $repository 'Editable-Tabs-Runtime.ps1')
    $loaderFunction = ${function:Install-EditableTabsLoader}
    $elevationFirefox = Fake-Firefox 'protected Firefox' '158.0.1'
    $elevation = [pscustomobject]@{ Verb=$null; Arguments=$null; ExitCode=0 }
    function Write-Status { param($Message, $Color) }
    function Install-EditableTabsLoader { param($Directory); throw [UnauthorizedAccessException]::new('Fixture requires elevation') }
    function Start-Process {
        param($FilePath, $ArgumentList, $Verb, $WindowStyle, [switch]$Wait, [switch]$PassThru)
        $elevation.Verb = $Verb
        $elevation.Arguments = $ArgumentList
        if ($elevation.ExitCode -eq 0) { & $loaderFunction -Directory (Split-Path -Parent $elevationFirefox) }
        return [pscustomobject]@{ ExitCode=$elevation.ExitCode }
    }
    try {
        $elevatedRuntime = Initialize-EditableTabsRuntime -SourceExecutable $elevationFirefox
        Check ($elevation.Verb -eq 'RunAs' -and $elevation.Arguments.Contains('Install-Editable-Tabs-Loader.ps1')) 'protected Firefox requests elevation for only the loader helper'
        Check ($elevatedRuntime.InPlace -and $elevatedRuntime.Executable -eq $elevationFirefox) 'elevation keeps the existing Firefox executable'
        $elevation.ExitCode = 1
        $elevationFailed = $false
        try { Initialize-EditableTabsRuntime -SourceExecutable $elevationFirefox } catch { $elevationFailed = $_.Exception.Message -match 'loader setup failed' }
        Check $elevationFailed 'failed elevated loader setup aborts installation'
    } finally {
        Set-Item Function:\Install-EditableTabsLoader -Value $loaderFunction
        Remove-Item Function:\Start-Process
    }
    Write-Host "Result: $checks installer checks passed"
} finally {
    $resolved = [IO.Path]::GetFullPath($testRoot)
    if (-not $resolved.StartsWith($temporaryBase + '\whitesur-installer-tests-', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Refusing to clean a path outside the installer test workspace.'
    }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
