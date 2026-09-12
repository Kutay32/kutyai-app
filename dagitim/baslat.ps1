<#
.SYNOPSIS
  KutyAI dagitimini baslatir: .env uretir, sirlari olusturur, imajlari derler,
  servisleri kaldirir ve saglikli olana kadar bekler.

.DESCRIPTION
  Sirasiyla:
    1. Docker daemon denetimi (gerekirse Docker Desktop'i baslatmayi dener).
    2. .env yoksa .env.ornek'ten uretir; bos KUTYAI_GIZLI_ANAHTAR ve
       KUTYAI_SIFRELEME_ANAHTARI degerlerini uretir.
    3. `docker compose up -d --build` calistirir (istenen profil ile).
    4. Uc servisin sagligini bekler ve erisim adreslerini yazar.

.PARAMETER Profil
  postgres: PostgreSQL profili (veritabani URL'i otomatik ayarlanir).
  nginx:    Tek giris noktasi (http://localhost:8080).

.PARAMETER YenidenDerle
  Imajlari onbellek kullanmadan bastan derler (--no-cache).

.EXAMPLE
  .\baslat.ps1
  .\baslat.ps1 -Profil postgres
#>
[CmdletBinding()]
param(
    [ValidateSet("yok", "postgres", "nginx")]
    [string]$Profil = "yok",
    [switch]$YenidenDerle
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

function Yaz([string]$Metin, [string]$Renk = "Gray") {
    Write-Host $Metin -ForegroundColor $Renk
}

function Yeni-Base64Url([int]$Bayt, [switch]$Dolgusuz) {
    $tampon = New-Object byte[] $Bayt
    $uretec = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $uretec.GetBytes($tampon)
    $uretec.Dispose()
    $metin = [Convert]::ToBase64String($tampon).Replace('+', '-').Replace('/', '_')
    if ($Dolgusuz) { $metin = $metin.TrimEnd('=') }
    return $metin
}

# .env dosyasini BOM'suz UTF-8 okur/yazar (Turkce aciklamalar bozulmasin).
function Oku-Dosya([string]$Yol) {
    return [System.IO.File]::ReadAllText($Yol, (New-Object System.Text.UTF8Encoding($false)))
}

function Yaz-Dosya([string]$Yol, [string]$Metin) {
    [System.IO.File]::WriteAllText($Yol, $Metin, (New-Object System.Text.UTF8Encoding($false)))
}

# Yalnizca bos birakilmis degeri doldurur; kullanicinin yazdigi degere dokunmaz.
function Doldur([string]$Metin, [string]$Ad, [string]$Deger) {
    $desen = "(?m)^" + [regex]::Escape($Ad) + "=[ `t]*\r?$"
    return [regex]::Replace($Metin, $desen, ($Ad + "=" + $Deger))
}

function Oku([string]$Metin, [string]$Ad) {
    $eslesme = [regex]::Match($Metin, "(?m)^" + [regex]::Escape($Ad) + "=(.*)$")
    if ($eslesme.Success) { return $eslesme.Groups[1].Value.Trim() }
    return ""
}

function Bekle-Saglik([string]$Adres, [int]$Saniye, [string]$Etiket) {
    $bitis = (Get-Date).AddSeconds($Saniye)
    while ((Get-Date) -lt $bitis) {
        try {
            $yanit = Invoke-WebRequest -Uri $Adres -UseBasicParsing -TimeoutSec 5
            if ($yanit.StatusCode -eq 200) {
                Yaz ("  [tamam] {0} -> {1}" -f $Etiket, $Adres) "Green"
                return $true
            }
        } catch {
            Start-Sleep -Seconds 3
        }
    }
    Yaz ("  [HATA ] {0} saglikli olmadi: {1}" -f $Etiket, $Adres) "Red"
    return $false
}

Yaz ""
Yaz "KutyAI dagitimi baslatiliyor" "Cyan"
Yaz "===========================" "Cyan"

# --- 1) Docker denetimi -------------------------------------------------------
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Yaz "Docker bulunamadi. Docker Desktop kurun: https://docs.docker.com/get-docker/" "Red"
    exit 1
}
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Yaz "Docker daemon calismiyor; Docker Desktop baslatilmayi deniyor..." "Yellow"
    docker desktop start *> $null
    $son = (Get-Date).AddSeconds(120)
    while ((Get-Date) -lt $son) {
        Start-Sleep -Seconds 5
        docker info *> $null
        if ($LASTEXITCODE -eq 0) { break }
    }
    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        Yaz "Docker daemon baslatilamadi. Docker Desktop'i acip yeniden deneyin." "Red"
        exit 1
    }
}
Yaz "[1/4] Docker daemon hazir." "Green"

# --- 2) .env ve sirlar --------------------------------------------------------
if (-not (Test-Path ".env")) {
    Copy-Item ".env.ornek" ".env"
    Yaz "[2/4] .env yoktu; .env.ornek'ten uretildi." "Yellow"
} else {
    Yaz "[2/4] .env mevcut; eksik sirlar tamamlanacak." "Green"
}

$icerik = Oku-Dosya ".env"
$degisti = $false

if (-not (Oku $icerik "KUTYAI_GIZLI_ANAHTAR")) {
    $icerik = Doldur $icerik "KUTYAI_GIZLI_ANAHTAR" (Yeni-Base64Url 48 -Dolgusuz)
    $degisti = $true
    Yaz "      KUTYAI_GIZLI_ANAHTAR uretildi." "Yellow"
}
if (-not (Oku $icerik "KUTYAI_SIFRELEME_ANAHTARI")) {
    # Fernet anahtari: 32 rastgele baytin urlsafe base64 hali (dolgulu).
    $icerik = Doldur $icerik "KUTYAI_SIFRELEME_ANAHTARI" (Yeni-Base64Url 32)
    $degisti = $true
    Yaz "      KUTYAI_SIFRELEME_ANAHTARI uretildi." "Yellow"
}

$profilArg = @()
if ($Profil -eq "postgres") {
    if (-not (Oku $icerik "KUTYAI_POSTGRES_PAROLA")) {
        $icerik = Doldur $icerik "KUTYAI_POSTGRES_PAROLA" (Yeni-Base64Url 24 -Dolgusuz)
        $degisti = $true
    }
    $kullanici = Oku $icerik "KUTYAI_POSTGRES_KULLANICI"
    if (-not $kullanici) { $kullanici = "kutyai" }
    $veritabani = Oku $icerik "KUTYAI_POSTGRES_VERITABANI"
    if (-not $veritabani) { $veritabani = "kutyai" }
    $parola = Oku $icerik "KUTYAI_POSTGRES_PAROLA"
    $env:KUTYAI_VERITABANI_URL = "postgresql+asyncpg://${kullanici}:${parola}@postgres:5432/${veritabani}"
    $profilArg = @("--profile", "postgres")
    Yaz "      PostgreSQL profili: KUTYAI_VERITABANI_URL=$($env:KUTYAI_VERITABANI_URL)" "Yellow"
} elseif ($Profil -eq "nginx") {
    $profilArg = @("--profile", "nginx")
}

if ($degisti) { Yaz-Dosya ".env" $icerik }

# --- 3) Derleme ve kaldirma ---------------------------------------------------
$derlemeArg = @()
if ($YenidenDerle) { $derlemeArg = @("--no-cache") }

Yaz "[3/4] Imajlar derleniyor ve servisler kaldiriliyor (ilk derleme uzun surebilir)..." "Cyan"
& docker compose @profilArg up -d --build @derlemeArg
if ($LASTEXITCODE -ne 0) {
    Yaz "docker compose up basarisiz oldu." "Red"
    exit 1
}

# --- 4) Saglik beklemesi ------------------------------------------------------
Yaz "[4/4] Saglik bekleniyor..." "Cyan"
$saglikli = $true
$saglikli = (Bekle-Saglik "http://localhost:8000/api/v1/saglik" 180 "arkauc") -and $saglikli
$saglikli = (Bekle-Saglik "http://localhost:3000/" 120 "onuc") -and $saglikli
$saglikli = (Bekle-Saglik "http://localhost:3001/" 120 "yonetim_paneli") -and $saglikli
if ($Profil -eq "nginx") {
    $saglikli = (Bekle-Saglik "http://localhost:8080/" 60 "nginx") -and $saglikli
}

Yaz ""
if ($saglikli) {
    Yaz "KutyAI ayakta." "Green"
} else {
    Yaz "Bazi servisler saglikli degil; gunlukler icin: docker compose logs -f" "Yellow"
}
Yaz ""
Yaz "Erisim adresleri:" "Cyan"
Yaz "  API          http://localhost:8000/api/v1/saglik"
Yaz "  API belge    http://localhost:8000/api/docs"
Yaz "  Son kullanici http://localhost:3000"
Yaz "  Yonetim paneli http://localhost:3001"
if ($Profil -eq "nginx") { Yaz "  Tek giris     http://localhost:8080" }
Yaz ""
Yaz "Durum:      docker compose ps"
Yaz "Gunlukler:  docker compose logs -f <servis>"
Yaz "Durdurma:   docker compose down"
Yaz ""

if (-not $saglikli) { exit 1 }
