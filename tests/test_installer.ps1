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
    Check (Test-Path -LiteralPath $state.Shortcut) 'default install creates a profile-specific launcher'
    Check ($state.Executable -eq (Join-Path $runtime 'firefox.exe')) 'launcher uses the isolated Firefox copy'
    Check ([IO.File]::ReadAllText((Join-Path $first 'user.js')).Contains('user_pref("userChrome.tabSearch.enabled", true);')) 'editable tabs are enabled by default'
    Check (Test-Path -LiteralPath (Join-Path $first 'chrome\tab-search.uc.js')) 'profile contains the runtime script'
    $prefBytes = [IO.File]::ReadAllBytes((Join-Path $runtime 'defaults\pref\whitesur-autoconfig.js'))
    Check (-not ($prefBytes -contains 13) -and $prefBytes[0] -eq 112) 'AutoConfig preferences use LF and UTF-8 without BOM'
    Check ([IO.File]::ReadAllText((Join-Path $runtime 'whitesur.cfg')).StartsWith('//')) 'AutoConfig starts with the required comment'

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
    & $installer -ProfilePath $olderProfile -FirefoxPath $old -RuntimeDirectory (Join-Path $testRoot 'old-runtime') -ShortcutDirectory $shortcuts -Force
    Check (-not (Test-Path -LiteralPath (Join-Path $olderProfile '.whitesur-editable-tabs.json'))) 'older Firefox falls back to CSS without a runtime launcher'
    Check ([IO.File]::ReadAllText((Join-Path $olderProfile 'user.js')).Contains('tabSearch.enabled", false')) 'older Firefox retains the classic toolbar'

    $conflicting = Fake-Firefox 'source-configured' '158.0.1'
    $foreignPref = Join-Path (Split-Path -Parent $conflicting) 'defaults\pref\corporate.js'
    $foreignText = 'pref("general.config.filename", "corporate.cfg");'
    [IO.File]::WriteAllText($foreignPref, $foreignText)
    $configuredProfile = Profile 'configured'
    & $installer -ProfilePath $configuredProfile -FirefoxPath $conflicting -RuntimeDirectory (Join-Path $testRoot 'foreign-runtime') -Force
    Check ([IO.File]::ReadAllText($foreignPref) -eq $foreignText) 'existing AutoConfig remains untouched'
    Check (-not (Test-Path -LiteralPath (Join-Path $configuredProfile '.whitesur-editable-tabs.json'))) 'AutoConfig conflicts use the classic fallback'

    $unmanaged = Join-Path $testRoot 'unmanaged-runtime'
    New-Item -ItemType Directory -Path $unmanaged | Out-Null
    [IO.File]::WriteAllText((Join-Path $unmanaged 'sentinel.txt'), 'keep me')
    $guardedProfile = Profile 'guarded'
    & $installer -ProfilePath $guardedProfile -FirefoxPath $modern -RuntimeDirectory $unmanaged -Force
    Check ([IO.File]::ReadAllText((Join-Path $unmanaged 'sentinel.txt')) -eq 'keep me') 'unmanaged runtime directories are preserved'
    Check (-not (Test-Path -LiteralPath (Join-Path $unmanaged 'firefox.exe'))) 'failed runtime setup cannot overwrite an unrelated directory'
    Write-Host "Result: $checks installer checks passed"
} finally {
    $resolved = [IO.Path]::GetFullPath($testRoot)
    if (-not $resolved.StartsWith($temporaryBase + '\whitesur-installer-tests-', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Refusing to clean a path outside the installer test workspace.'
    }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
