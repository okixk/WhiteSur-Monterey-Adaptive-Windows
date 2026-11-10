#requires -Version 5.1
# Security fixtures only; never searches or modifies installed Firefox/profiles.
$ErrorActionPreference = 'Stop'
$repository = Split-Path -Parent $PSScriptRoot
$installer = Join-Path $repository 'Install-WhiteSur-Monterey-Adaptive.ps1'
$lab = Join-Path ([IO.Path]::GetTempPath()) ('whitesur-compatible-' + [guid]::NewGuid().ToString('N'))
$checks = 0
function Check([bool]$Condition, [string]$Message) {
    if (-not $Condition) { throw "FAIL: $Message" }
    $script:checks++
    Write-Host "PASS: $Message"
}
function Snapshot([string]$Directory) {
    return ((Get-ChildItem -LiteralPath $Directory -File -Recurse | Sort-Object FullName | ForEach-Object {
        $_.FullName + ':' + (Get-FileHash -LiteralPath $_.FullName).Hash
    }) -join "`n")
}
New-Item -ItemType Directory -Path $lab | Out-Null
try {
    foreach ($case in @('clean', 'old', 'inline', 'multiline', 'dynamic', 'orphan', 'policy', 'custom-defaults', 'invalid-marker')) {
        $directory = Join-Path $lab $case
        $prefDirectory = Join-Path $directory 'defaults\pref'
        New-Item -ItemType Directory -Path $prefDirectory -Force | Out-Null
        [IO.File]::WriteAllText((Join-Path $directory 'firefox.exe'), 'fixture, never launched')
        $version = if ($case -eq 'old') { '154.0' } else { '159.0' }
        [IO.File]::WriteAllText((Join-Path $directory 'application.ini'), "[App]`nVersion=$version`n")
        $pref = switch ($case) {
            'inline' { '/* company config */ pref("general.config.filename", "zscaler.cfg");' }
            'multiline' { "pref(`n'general.config.filename',`n'zscaler.cfg');" }
            'dynamic' { 'const name = "zscaler.cfg"; pref("general.config.filename", name);' }
            default { $null }
        }
        if ($pref) {
            [IO.File]::WriteAllText((Join-Path $prefDirectory 'company.js'), $pref)
            [IO.File]::WriteAllText((Join-Path $directory 'zscaler.cfg'), '// harmless lab fixture')
        }
        if ($case -eq 'orphan') { [IO.File]::WriteAllText((Join-Path $directory 'zscaler.cfg'), '// preserved even without a filename pref') }
        if ($case -eq 'invalid-marker') { [IO.File]::WriteAllText((Join-Path $directory '.whitesur-loader.json'), '{bad json') }
        if ($case -eq 'custom-defaults') { [IO.File]::WriteAllText((Join-Path $prefDirectory 'security.js'), 'pref("security.tls.version.min", 3);') }
        if ($case -eq 'policy') {
            New-Item -ItemType Directory -Path (Join-Path $directory 'distribution') | Out-Null
            [IO.File]::WriteAllText((Join-Path $directory 'distribution\policies.json'), '{"policies":{"DisableTelemetry":true}}')
        }
        $profile = Join-Path $lab ($case + '-profile')
        New-Item -ItemType Directory -Path (Join-Path $profile 'chrome') -Force | Out-Null
        [IO.File]::WriteAllText((Join-Path $profile 'chrome\original.css'), '/* original */')
        [IO.File]::WriteAllText((Join-Path $profile 'user.js'), 'user_pref("other.preference", true);')
        $before = Snapshot $directory
        $binary = Join-Path $directory 'firefox.exe'
        & $installer -ProfilePath $profile -FirefoxPath $binary -Force
        Check ((Snapshot $directory) -ceq $before) "$case default Full leaves every installation file unchanged"
        Check ((Test-Path -LiteralPath (Join-Path $profile 'chrome\full-compatible.css')) -and
            -not (Test-Path -LiteralPath (Join-Path $profile 'chrome\tab-search.uc.js'))) "$case receives Full CSS without privileged JavaScript"
        & $installer -ProfilePath $profile -FirefoxPath $binary -Diagnose
        Check ((Snapshot $directory) -ceq $before) "$case diagnostics are read only"
        if ($case -in @('inline','multiline','dynamic','orphan','invalid-marker')) {
            $failed = $false
            try { & $installer -ProfilePath $profile -FirefoxPath $binary -InstallationMethod AutoConfig -Force }
            catch { $failed = $true }
            Check ($failed -and ((Snapshot $directory) -ceq $before)) "$case rejects explicit legacy loading without changing configuration"
        }
        if ($case -in @('policy','custom-defaults')) {
            $failed = $false
            $runtime = Join-Path $lab ($case + '-runtime')
            try { & $installer -ProfilePath $profile -FirefoxPath $binary -RuntimeDirectory $runtime -Force }
            catch { $failed = $true }
            Check ($failed -and ((Snapshot $directory) -ceq $before) -and -not (Test-Path -LiteralPath $runtime)) "$case refuses legacy copying instead of transplanting security configuration"
            if ($case -eq 'policy') {
                $failed = $false
                try { & $installer -ProfilePath $profile -FirefoxPath $binary -InstallationMethod AutoConfig -Force }
                catch { $failed = $true }
                Check ($failed -and ((Snapshot $directory) -ceq $before)) 'policy-managed Firefox also refuses a new in-place legacy loader'
            }
        }
        & $installer -ProfilePath $profile -FirefoxPath $binary -Uninstall -Force
        Check (([IO.File]::ReadAllText((Join-Path $profile 'chrome\original.css'))) -eq '/* original */') "$case uninstall restores the theme"
        Check ((Snapshot $directory) -ceq $before) "$case uninstall preserves all installation files"
    }
    # An owned marker does not authorize replacing an existing cfg file.
    $owned = Join-Path $lab 'owned'
    New-Item -ItemType Directory -Path $owned | Out-Null
    [IO.File]::WriteAllText((Join-Path $owned 'firefox.exe'), 'fixture')
    [IO.File]::WriteAllText((Join-Path $owned 'application.ini'), "[App]`nVersion=159.0`n")
    [IO.File]::WriteAllText((Join-Path $owned '.whitesur-loader.json'), '{"Owner":"WhiteSur-Monterey-Adaptive-Windows","Ready":true}')
    [IO.File]::WriteAllText((Join-Path $owned 'whitesur.cfg'), '// existing changed cfg')
    $before = Snapshot $owned
    $failed = $false
    try { & $installer -ProfilePath $profile -FirefoxPath (Join-Path $owned 'firefox.exe') -InstallationMethod AutoConfig -Force }
    catch { $failed = $_.Exception.Message -match 'preserved' }
    Check ($failed -and ((Snapshot $owned) -ceq $before)) 'ownership never authorizes modifying an existing AutoConfig file'
    $cleanBinary = Join-Path $lab 'clean\firefox.exe'
    & $installer -ProfilePath $profile -FirefoxPath $cleanBinary -InstallationMethod AutoConfig -Force
    $shared = Snapshot (Split-Path -Parent $cleanBinary)
    & $installer -ProfilePath $profile -FirefoxPath $cleanBinary -Force
    Check (((Snapshot (Split-Path -Parent $cleanBinary)) -ceq $shared) -and
        -not (Test-Path -LiteralPath (Join-Path $profile 'chrome\tab-search.uc.js'))) 'old Full migrates to CSS without changing its shared AutoConfig'
    Check ([IO.File]::ReadAllText((Join-Path $profile 'user.js')).Contains('tabSearch.enabled", false')) 'CSS migration disables the old profile loader preference'
    $ignoredRuntime = Join-Path $lab 'ignored-runtime'
    & $installer -ProfilePath $profile -FirefoxPath $cleanBinary -InstallationMethod Compatible -RuntimeDirectory $ignoredRuntime -Force
    Check (-not (Test-Path -LiteralPath $ignoredRuntime)) 'explicit Compatible overrides legacy runtime arguments'
    Write-Host "Result: $checks compatible installer checks passed"
} finally {
    $resolved = [IO.Path]::GetFullPath($lab)
    if (-not $resolved.StartsWith([IO.Path]::GetFullPath([IO.Path]::GetTempPath()), [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe lab cleanup path' }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
