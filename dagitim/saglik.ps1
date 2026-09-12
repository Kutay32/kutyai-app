<#
.SYNOPSIS
  KutyAI servislerinin sagligini yoklar: arkauc (API), onuc, yonetim_paneli.

.DESCRIPTION
  Uc servise HTTP istegi atar, Turkce ozet ve konteyner durumunu yazar.
  Hepsi saglikliysa cikis kodu 0, degilse 1 doner (zamanlanmis gorevlerde kullanilabilir).

.EXAMPLE
  .\saglik.ps1
#>
[CmdletBinding()]
param()

Set-Location -Path $PSScriptRoot

$kontroller = @(
    [pscustomobject]@{ Ad = "arkauc";         Adres = "http://localhost:8000/api/v1/saglik" },
    [pscustomobject]@{ Ad = "onuc";           Adres = "http://localhost:3000/" },
    [pscustomobject]@{ Ad = "yonetim_paneli"; Adres = "http://localhost:3001/" }
)

Write-Host ""
Write-Host "KutyAI saglik kontrolu" -ForegroundColor Cyan
Write-Host "======================" -ForegroundColor Cyan

$hataVar = $false

foreach ($k in $kontroller) {
    $kod = 0
    $not = ""
    try {
        $yanit = Invoke-WebRequest -Uri $k.Adres -UseBasicParsing -TimeoutSec 5
        $kod = [int]$yanit.StatusCode
        $govde = $yanit.Content
        if ($k.Ad -eq "arkauc") {
            try {
                $nesne = $govde | ConvertFrom-Json
                if ($nesne.durum) { $not = ("uygulama: {0}, surum {1}" -f $nesne.durum, $nesne.surum) }
            } catch {
                $not = "govde okunamadi"
            }
        }
    } catch {
        $kod = 0
        $yanit = $_.Exception.Response
        if ($yanit -and $yanit.StatusCode) {
            $kod = [int]$yanit.StatusCode
            $not = "beklenmeyen durum kodu"
        } else {
            $not = "erisilemedi"
        }
    }

    if ($kod -eq 200) {
        if (-not $not) { $not = "yanit veriyor" }
        Write-Host ("  [TAMAM] {0,-16} {1}  HTTP {2}  ({3})" -f $k.Ad, $k.Adres, $kod, $not) -ForegroundColor Green
    } else {
        $hataVar = $true
        if ($kod -eq 0) { $kod = "-" }
        Write-Host ("  [HATA ] {0,-16} {1}  HTTP {2}  ({3})" -f $k.Ad, $k.Adres, $kod, $not) -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "Konteyner durumu:" -ForegroundColor Cyan
try {
    docker compose ps --format "{{.Service}}`t{{.State}}`t{{.Health}}" 2>$null |
        ForEach-Object { Write-Host ("  {0}" -f $_) }
} catch {
    Write-Host "  (docker compose ps okunamadi)" -ForegroundColor Yellow
}

Write-Host ""
if ($hataVar) {
    Write-Host "SONUC: bazi servisler saglikli degil." -ForegroundColor Red
    Write-Host "Gunlukler: docker compose logs -f <servis>" -ForegroundColor Yellow
    exit 1
}

Write-Host "SONUC: tum servisler saglikli." -ForegroundColor Green
exit 0
