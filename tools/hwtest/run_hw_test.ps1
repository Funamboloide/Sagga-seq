# SAGGA SEQ: il test sull'FM-1 vero, da PowerShell, con l'FM-1 collegato via USB e FERMO (non in PLAY).
# Nella cartella dello zip scompattato:
#     powershell -ExecutionPolicy Bypass -File .\run_hw_test.ps1
# Opzioni passate al programma, per esempio:   ... -File .\run_hw_test.ps1 --bars 8      oppure   --port Felucca
# Chiudi prima Ableton o qualunque programma che tenga aperte le porte MIDI dell'FM-1 (su Windows sono esclusive).
Set-Location $PSScriptRoot
$py = $null
foreach ($c in "py -3.12", "py -3.11", "py -3", "python", "python3") {
    try { $v = Invoke-Expression "$c --version 2>&1" } catch { continue }
    if ("$v" -match "Python 3\.(9|[1-9]\d)") { $py = $c; break }
}
if (-not $py) {
    Write-Host "Python 3.9 o piu' recente non trovato: https://www.python.org/downloads/ (spunta 'Add python.exe to PATH'), poi rilancia."
    Read-Host "Invio per chiudere" | Out-Null
    exit 1
}
Write-Host "Python: $py. Controllo mido e python-rtmidi..."
Invoke-Expression "$py -m pip install --quiet --disable-pip-version-check mido python-rtmidi"
if ($LASTEXITCODE -ne 0) { Write-Host "pip non riesce a installare mido / python-rtmidi: serve internet la prima volta." }
Invoke-Expression "$py sagga_hw_test.py $($args -join ' ')"
$rc = $LASTEXITCODE
Write-Host ""
if ($rc -eq 0) { Write-Host "Tutto passato. Il log e il backup del progetto sono in questa cartella." }
else { Write-Host "Qualcosa non va (codice $rc): manda il file hwtest-*.log piu' recente di questa cartella." }
Read-Host "Invio per chiudere" | Out-Null
exit $rc
