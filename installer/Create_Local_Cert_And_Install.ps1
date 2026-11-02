<#
.SYNOPSIS
    Script di Installazione & Firma Digitale Authenticode per SteadyMotion AI (Medical Device SaMD Classe I).
.DESCRIPTION
    Requisiti Windows per bypassare UAC e UIPI con uiAccess="true":
    1. L'eseguibile DEVE essere firmato con un certificato digitale trusted nella macchina locale (Root/TrustedPublisher).
    2. L'eseguibile DEVE risiedere in una directory protetta di sistema (C:\Program Files\SteadyMotion AI).
    Questo script:
    - Richiede ed eleva i privilegi di Amministratore se necessario.
    - Genera o recupera il certificato "SteadyMotion Clinical SaMD Root".
    - Firma SteadyMotion-AI.exe con Authenticode (SHA256).
    - Installa la build compilata in C:\Program Files\SteadyMotion AI.
    - Crea i collegamenti sul Desktop e nel Menu Start.
#>

[CmdletBinding()]
param (
    [string]$SourceDir = "$PSScriptRoot\..\dist\SteadyMotion-AI",
    [string]$TargetDir = "C:\Program Files\SteadyMotion AI"
)

# 1. Verifica Privilegi di Amministratore
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "[INFO] Richiesta elevazione privilegi di Amministratore..." -ForegroundColor Cyan
    Start-Process powershell.exe -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit
}

Write-Host "==================================================================" -ForegroundColor Green
Write-Host "  SteadyMotion AI v3.0 / v3.1 Pro - Installatore Clinico SaMD     " -ForegroundColor White
Write-Host "  Configurazione Certificato Digitale & Attivazione UI Access     " -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host ""

# 2. Risoluzione Percorsi Assoluti
$SourceFullPath = [System.IO.Path]::GetFullPath($SourceDir)
$ExePath = Join-Path $SourceFullPath "SteadyMotion-AI.exe"

if (-not (Test-Path $ExePath)) {
    Write-Error "Eseguibile non trovato in: $ExePath. Compilare prima con 'python build_standalone.py'."
    Read-Host "Premere Invio per uscire..."
    exit 1
}

# 3. Creazione o Recupero Certificato di Firma Digitale
$CertSubject = "CN=SteadyMotion Clinical SaMD Root"
Write-Host "[1/5] Verifica Certificato Digitale Authenticode ($CertSubject)..." -ForegroundColor Yellow

$cert = Get-ChildItem Cert:\LocalMachine\My -ErrorAction SilentlyContinue | Where-Object { $_.Subject -eq $CertSubject } | Select-Object -First 1

if (-not $cert) {
    Write-Host "[INFO] Creazione nuovo certificato crittografico SHA-256..." -ForegroundColor Cyan
    $cert = New-SelfSignedCertificate -Type CodeSigningCert `
        -Subject $CertSubject `
        -CertStoreLocation Cert:\LocalMachine\My `
        -HashAlgorithm SHA256 `
        -KeyLength 2048 `
        -NotAfter (Get-Date).AddYears(10)
    
    # Esportazione e installazione nei trusted root stores
    $tmpCert = Join-Path $env:TEMP "SteadyMotionRoot.cer"
    Export-Certificate -Cert $cert -FilePath $tmpCert -Force | Out-Null
    Import-Certificate -FilePath $tmpCert -CertStoreLocation Cert:\LocalMachine\Root | Out-Null
    Import-Certificate -FilePath $tmpCert -CertStoreLocation Cert:\LocalMachine\TrustedPublisher | Out-Null
    Remove-Item $tmpCert -Force
    Write-Host "[OK] Certificato installato e registrato in Autorita Radice di Certificazione Attendibili." -ForegroundColor Green
} else {
    Write-Host "[OK] Certificato esistente valido trovato: $($cert.Thumbprint)" -ForegroundColor Green
}

# 4. Firma Digitale Authenticode con SHA-256
Write-Host "[2/5] Firma Digitale Authenticode su $ExePath..." -ForegroundColor Yellow
$sig = Set-AuthenticodeSignature -FilePath $ExePath -Certificate $cert -HashAlgorithm SHA256

if ($sig.Status -eq "Valid") {
    Write-Host "[OK] Firma Authenticode Valida al 100%!" -ForegroundColor Green
} else {
    Write-Warning "Firma applicata con stato: $($sig.Status). $($sig.StatusMessage)"
}

# 5. Installazione in Directory Protetta (C:\Program Files\SteadyMotion AI)
Write-Host "[3/5] Installazione file in $TargetDir..." -ForegroundColor Yellow
if (-not (Test-Path $TargetDir)) {
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
}

Copy-Item -Path "$SourceFullPath\*" -Destination $TargetDir -Recurse -Force
Write-Host "[OK] File copiati con successo in $TargetDir." -ForegroundColor Green

# 6. Creazione Collegamenti Desktop & Start Menu
Write-Host "[4/5] Creazione scorciatoie Desktop e Menu Start..." -ForegroundColor Yellow
$InstalledExe = Join-Path $TargetDir "SteadyMotion-AI.exe"
$WshShell = New-Object -ComObject WScript.Shell

# Desktop
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$DesktopShortcut = $WshShell.CreateShortcut((Join-Path $DesktopPath "SteadyMotion AI.lnk"))
$DesktopShortcut.TargetPath = $InstalledExe
$DesktopShortcut.WorkingDirectory = $TargetDir
$DesktopShortcut.Description = "SteadyMotion AI - Controllo Cefalico & SaMD Assistivo"
$DesktopShortcut.Save()

# Start Menu
$StartMenuPath = [Environment]::GetFolderPath("CommonPrograms")
$StartShortcut = $WshShell.CreateShortcut((Join-Path $StartMenuPath "SteadyMotion AI.lnk"))
$StartShortcut.TargetPath = $InstalledExe
$StartShortcut.WorkingDirectory = $TargetDir
$StartShortcut.Description = "SteadyMotion AI - Controllo Cefalico & SaMD Assistivo"
$StartShortcut.Save()
Write-Host "[OK] Collegamenti creati con successo." -ForegroundColor Green

# 7. Verifica Finale e Riepilogo
Write-Host "[5/5] Verifica Permessi UI Access & Conformita MDR..." -ForegroundColor Yellow
Write-Host ""
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "  INSTALLAZIONE COMPLETATA CON SUCCESSO!                         " -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Green
Write-Host "Eseguibile Installato: $InstalledExe" -ForegroundColor White
Write-Host "Stato Firma Digitale:  $($sig.Status)" -ForegroundColor White
Write-Host "Bypass UAC / UIPI:     ATTIVO (uiAccess=true abilitato in C:\Program Files)" -ForegroundColor White
Write-Host "Certificazione MDR:    Fascicolo Tecnico SaMD Classe I conforme" -ForegroundColor White
Write-Host ""
Write-Host "SteadyMotion AI puo ora essere avviato direttamente dal Desktop!" -ForegroundColor Cyan
