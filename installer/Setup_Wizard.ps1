<#
.SYNOPSIS
    Installatore Grafico Ufficiale (GUI Setup Wizard) per SteadyMotion AI Pro.
    Non richiede software di terze parti o compiler esterni; opera nativamente su Windows Forms.
#>

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

# 1. Verifica ed elevazione Amministratore
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Start-Process powershell.exe -Verb RunAs -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    exit
}

[System.Windows.Forms.Application]::EnableVisualStyles()

# 2. Finestra Principale Setup
$form = New-Object System.Windows.Forms.Form
$form.Text = "SteadyMotion AI Pro — Installazione Guidata (MDR SaMD)"
$form.Size = New-Object System.Drawing.Size(560, 460)
$form.StartPosition = "CenterScreen"
$form.FormBorderStyle = "FixedDialog"
$form.MaximizeBox = $false
$form.MinimizeBox = $false
$form.BackColor = [System.Drawing.Color]::FromArgb(248, 250, 252)

# Banner Superiore
$banner = New-Object System.Windows.Forms.Panel
$banner.Size = New-Object System.Drawing.Size(560, 80)
$banner.BackColor = [System.Drawing.Color]::FromArgb(15, 23, 42)
$banner.Location = New-Object System.Drawing.Point(0, 0)
$form.Controls.Add($banner)

$lblTitle = New-Object System.Windows.Forms.Label
$lblTitle.Text = "STEADYMOTION AI PRO"
$lblTitle.Font = New-Object System.Drawing.Font("Segoe UI", 16, [System.Drawing.FontStyle]::Bold)
$lblTitle.ForeColor = [System.Drawing.Color]::FromArgb(56, 189, 248)
$lblTitle.Location = New-Object System.Drawing.Point(20, 16)
$lblTitle.AutoSize = $true
$banner.Controls.Add($lblTitle)

$lblSub = New-Object System.Windows.Forms.Label
$lblSub.Text = "Dispositivo Medico SaMD Classe I • Assistive Head Tracking & AAC"
$lblSub.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Regular)
$lblSub.ForeColor = [System.Drawing.Color]::FromArgb(148, 163, 184)
$lblSub.Location = New-Object System.Drawing.Point(22, 46)
$lblSub.AutoSize = $true
$banner.Controls.Add($lblSub)

# Corpo Centrale
$lblDesc = New-Object System.Windows.Forms.Label
$lblDesc.Text = "Benvenuto nell'installazione guidata di SteadyMotion AI Pro.`n`nQuesta procedura installerà il software nella cartella protetta di sistema, configurerà il certificato digitale Authenticode per consentire al paziente il controllo delle finestre UAC di Windows e creerà le scorciatoie sul Desktop."
$lblDesc.Font = New-Object System.Drawing.Font("Segoe UI", 10)
$lblDesc.ForeColor = [System.Drawing.Color]::FromArgb(51, 65, 85)
$lblDesc.Location = New-Object System.Drawing.Point(24, 100)
$lblDesc.Size = New-Object System.Drawing.Size(500, 85)
$form.Controls.Add($lblDesc)

# Cartella di Destinazione
$grpDest = New-Object System.Windows.Forms.GroupBox
$grpDest.Text = "Cartella di Installazione (Obbligatoria per UI Access)"
$grpDest.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Bold)
$grpDest.Location = New-Object System.Drawing.Point(24, 190)
$grpDest.Size = New-Object System.Drawing.Size(500, 65)
$form.Controls.Add($grpDest)

$txtDest = New-Object System.Windows.Forms.TextBox
$txtDest.Text = "C:\Program Files\SteadyMotion AI"
$txtDest.ReadOnly = $true
$txtDest.Font = New-Object System.Drawing.Font("Segoe UI", 10)
$txtDest.Location = New-Object System.Drawing.Point(16, 26)
$txtDest.Size = New-Object System.Drawing.Size(465, 26)
$grpDest.Controls.Add($txtDest)

# Barra di Avanzamento
$progressBar = New-Object System.Windows.Forms.ProgressBar
$progressBar.Location = New-Object System.Drawing.Point(24, 275)
$progressBar.Size = New-Object System.Drawing.Size(500, 24)
$progressBar.Style = "Continuous"
$progressBar.Value = 0
$form.Controls.Add($progressBar)

$lblStatus = New-Object System.Windows.Forms.Label
$lblStatus.Text = "Pronto per l'installazione."
$lblStatus.Font = New-Object System.Drawing.Font("Segoe UI", 9, [System.Drawing.FontStyle]::Italic)
$lblStatus.ForeColor = [System.Drawing.Color]::FromArgb(100, 116, 139)
$lblStatus.Location = New-Object System.Drawing.Point(24, 305)
$lblStatus.Size = New-Object System.Drawing.Size(500, 20)
$form.Controls.Add($lblStatus)

# Checkbox Avvia Subito
$chkLaunch = New-Object System.Windows.Forms.CheckBox
$chkLaunch.Text = "Avvia SteadyMotion AI Pro al termine dell'installazione"
$chkLaunch.Font = New-Object System.Drawing.Font("Segoe UI", 9.5)
$chkLaunch.Checked = $true
$chkLaunch.Location = New-Object System.Drawing.Point(24, 335)
$chkLaunch.Size = New-Object System.Drawing.Size(400, 24)
$form.Controls.Add($chkLaunch)

# Pulsanti Inferiori
$btnInstall = New-Object System.Windows.Forms.Button
$btnInstall.Text = "🚀 Installa Ora"
$btnInstall.Font = New-Object System.Drawing.Font("Segoe UI", 10, [System.Drawing.FontStyle]::Bold)
$btnInstall.BackColor = [System.Drawing.Color]::FromArgb(16, 185, 129)
$btnInstall.ForeColor = [System.Drawing.Color]::White
$btnInstall.FlatStyle = "Flat"
$btnInstall.Location = New-Object System.Drawing.Point(290, 375)
$btnInstall.Size = New-Object System.Drawing.Size(130, 36)
$form.Controls.Add($btnInstall)

$btnCancel = New-Object System.Windows.Forms.Button
$btnCancel.Text = "Annulla"
$btnCancel.Font = New-Object System.Drawing.Font("Segoe UI", 10)
$btnCancel.Location = New-Object System.Drawing.Point(430, 375)
$btnCancel.Size = New-Object System.Drawing.Size(95, 36)
$btnCancel.Add_Click({ $form.Close() })
$form.Controls.Add($btnCancel)

# Azione di Installazione
$btnInstall.Add_Click({
    $btnInstall.Enabled = $false
    $btnCancel.Enabled = $false
    
    $SourceDir = [System.IO.Path]::GetFullPath("$PSScriptRoot\..\dist\SteadyMotion-AI")
    $TargetDir = "C:\Program Files\SteadyMotion AI"

    # Step 1: Certificato
    $lblStatus.Text = "Configurazione certificato crittografico Authenticode..."
    $progressBar.Value = 25
    $form.Refresh()

    $CertSubject = "CN=SteadyMotion Clinical SaMD Root"
    $cert = Get-ChildItem Cert:\LocalMachine\My -ErrorAction SilentlyContinue | Where-Object { $_.Subject -eq $CertSubject } | Select-Object -First 1

    if (-not $cert) {
        $cert = New-SelfSignedCertificate -Type CodeSigningCert `
            -Subject $CertSubject `
            -CertStoreLocation Cert:\LocalMachine\My `
            -HashAlgorithm SHA256 `
            -KeyLength 2048 `
            -NotAfter (Get-Date).AddYears(10)
        
        $tmpCert = Join-Path $env:TEMP "SteadyMotionRoot.cer"
        Export-Certificate -Cert $cert -FilePath $tmpCert -Force | Out-Null
        Import-Certificate -FilePath $tmpCert -CertStoreLocation Cert:\LocalMachine\Root | Out-Null
        Import-Certificate -FilePath $tmpCert -CertStoreLocation Cert:\LocalMachine\TrustedPublisher | Out-Null
        Remove-Item $tmpCert -Force
    }

    # Step 2: Copia File
    $lblStatus.Text = "Copia dei file in C:\Program Files\SteadyMotion AI..."
    $progressBar.Value = 60
    $form.Refresh()

    if (-not (Test-Path $TargetDir)) {
        New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
    }
    Copy-Item -Path "$SourceDir\*" -Destination $TargetDir -Recurse -Force

    # Step 3: Firma Eseguibile
    $lblStatus.Text = "Applicazione firma Authenticode per permessi UI Access..."
    $progressBar.Value = 80
    $form.Refresh()

    $InstalledExe = Join-Path $TargetDir "SteadyMotion-AI.exe"
    if (Test-Path $InstalledExe) {
        Set-AuthenticodeSignature -FilePath $InstalledExe -Certificate $cert -HashAlgorithm SHA256 | Out-Null
    }

    # Step 4: Scorciatoie
    $lblStatus.Text = "Creazione scorciatoie Desktop e Menu Start..."
    $progressBar.Value = 95
    $form.Refresh()

    $WshShell = New-Object -ComObject WScript.Shell
    $DesktopPath = [Environment]::GetFolderPath("Desktop")
    $lnk = $WshShell.CreateShortcut((Join-Path $DesktopPath "SteadyMotion AI.lnk"))
    $lnk.TargetPath = $InstalledExe
    $lnk.WorkingDirectory = $TargetDir
    $lnk.Description = "SteadyMotion AI - Controllo Cefalico & SaMD Assistivo"
    $lnk.Save()

    $StartMenuPath = [Environment]::GetFolderPath("CommonPrograms")
    $lnkStart = $WshShell.CreateShortcut((Join-Path $StartMenuPath "SteadyMotion AI.lnk"))
    $lnkStart.TargetPath = $InstalledExe
    $lnkStart.WorkingDirectory = $TargetDir
    $lnkStart.Description = "SteadyMotion AI - Controllo Cefalico & SaMD Assistivo"
    $lnkStart.Save()

    # Step 5: Completamento
    $progressBar.Value = 100
    $lblStatus.Text = "✅ Installazione completata con successo!"
    $lblStatus.ForeColor = [System.Drawing.Color]::FromArgb(16, 185, 129)
    $btnCancel.Text = "Chiudi"
    $btnCancel.Enabled = $true
    $btnInstall.Visible = $false
    $form.Refresh()

    [System.Windows.Forms.MessageBox]::Show(
        "SteadyMotion AI Pro è stato installato con successo in C:\Program Files!`n`nPermessi UI Access (bypass UAC) attivati.`nScorciatoia creata sul Desktop.",
        "Installazione Riuscita",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Information
    ) | Out-Null

    if ($chkLaunch.Checked -and (Test-Path $InstalledExe)) {
        Start-Process $InstalledExe
    }
    $form.Close()
})

[void]$form.ShowDialog()
