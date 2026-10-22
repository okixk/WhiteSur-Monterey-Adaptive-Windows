#requires -Version 5.1
# Elevate only the loader write; profile installation stays with the original user.
[CmdletBinding()]
param([Parameter(Mandatory)][string]$FirefoxDirectory)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$PackageRoot = $PSScriptRoot
. (Join-Path $PackageRoot 'Editable-Tabs-Runtime.ps1')
try {
    Install-EditableTabsLoader -Directory $FirefoxDirectory
    exit 0
} catch {
    Write-Error -ErrorRecord $_ -ErrorAction Continue
    exit 1
}
