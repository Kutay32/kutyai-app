#!/usr/bin/env bash
# KutyAI dagitimini baslatir: .env uretir, sirlari olusturur, imajlari derler,
# servisleri kaldirir ve saglikli olana kadar bekler.
#
#   ./baslat.sh                      # SQLite (adlandirilmis volume)
#   ./baslat.sh --profil postgres    # PostgreSQL profili
#   ./baslat.sh --profil nginx       # tek giris noktasi (http://localhost:8080)
#   ./baslat.sh --yeniden-derle      # imajlari onbelleksiz derle
set -euo pipefail

cd "$(dirname "$0")"

PROFIL="yok"
YENIDEN_DERLE=""

kullanim() {
  cat <<'METIN'
KutyAI dagitimini baslatir: .env uretir, sirlari olusturur, imajlari derler,
servisleri kaldirir ve saglikli olana kadar bekler.

  ./baslat.sh                      # SQLite (adlandirilmis volume)
  ./baslat.sh --profil postgres    # PostgreSQL profili
  ./baslat.sh --profil nginx       # tek giris noktasi (http://localhost:8080)
  ./baslat.sh --yeniden-derle      # imajlari onbelleksiz derle
METIN
  exit 0
}

while [ $# -gt 0 ]; do
  case "$1" in
    --profil) PROFIL="${2:-}"; shift 2 ;;
    --profil=*) PROFIL="${1#*=}"; shift ;;
    --yeniden-derle) YENIDEN_DERLE="--no-cache"; shift ;;
    -h|--help) kullanim ;;
    *) echo "Bilinmeyen arguman: $1 (--help ile kullanimi gorun)" >&2; exit 2 ;;
  esac
done

case "$PROFIL" in
  yok|postgres|nginx) ;;
  *) echo "Gecersiz profil: $PROFIL (yok|postgres|nginx)" >&2; exit 2 ;;
esac

if [ -t 1 ]; then
  KIRMIZI=$'\033[31m'; YESIL=$'\033[32m'; SARI=$'\033[33m'; MAVI=$'\033[36m'; DUZ=$'\033[0m'
else
  KIRMIZI=""; YESIL=""; SARI=""; MAVI=""; DUZ=""
fi
yaz() { printf '%s%s%s\n' "$2" "$1" "$DUZ"; }

# 32/48 bayt rastgele veriyi urlsafe base64'e cevirir.
# NOT: openssl bazi platformlarda (Windows/MSYS) satiri CRLF ile bitirir; CR
# temizlenmezse anahtarin sonuna gorunmez bir karakter eklenir.
base64url() {
  local bayt="$1" dolgu="${2:-dolgulu}"
  if command -v openssl >/dev/null 2>&1; then
    if [ "$dolgu" = "dolgusuz" ]; then
      openssl rand -base64 "$bayt" | tr -d '\n\r=' | tr '+/' '-_'
    else
      openssl rand -base64 "$bayt" | tr -d '\n\r' | tr '+/' '-_'
    fi
  elif command -v python3 >/dev/null 2>&1; then
    python3 - "$bayt" "$dolgu" <<'PY'
import base64, os, sys
bayt, dolgu = int(sys.argv[1]), sys.argv[2]
metin = base64.urlsafe_b64encode(os.urandom(bayt)).decode()
print(metin if dolgu == "dolgulu" else metin.rstrip("="))
PY
  else
    echo "Sır uretmek icin openssl ya da python3 gerekir." >&2
    exit 1
  fi
}

# .env icindeki degeri okur (yoksa bos doner).
oku() {
  sed -n "s/^$1=//p" .env | head -n 1 | tr -d '\r' | sed 's/[[:space:]]*$//'
}

# Yalnizca bos birakilmis degeri doldurur; kullanicinin degerine dokunmaz.
doldur() {
  local ad="$1" deger="$2"
  if grep -qE "^${ad}=[[:space:]]*$" .env; then
    awk -v ad="$ad" -v d="$deger" \
      'BEGIN{ok=0} { if (ok==0 && $0 ~ "^"ad"=[[:space:]]*$") { print ad"="d; ok=1 } else print }' \
      .env > .env.gecici
    mv .env.gecici .env
  fi
}

echo
yaz "KutyAI dagitimi baslatiliyor" "$MAVI"
yaz "===========================" "$MAVI"

# --- 1) Docker denetimi -------------------------------------------------------
if ! command -v docker >/dev/null 2>&1; then
  yaz "Docker bulunamadi. Kurulum: https://docs.docker.com/get-docker/" "$KIRMIZI"
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  yaz "Docker daemon calismiyor; Docker Desktop baslatilmayi deniyor..." "$SARI"
  docker desktop start >/dev/null 2>&1 || true
  for _ in $(seq 1 24); do
    sleep 5
    docker info >/dev/null 2>&1 && break
  done
  if ! docker info >/dev/null 2>&1; then
    yaz "Docker daemon baslatilamadi. Docker Desktop'i acip yeniden deneyin." "$KIRMIZI"
    exit 1
  fi
fi
yaz "[1/4] Docker daemon hazir." "$YESIL"

# --- 2) .env ve sirlar --------------------------------------------------------
if [ ! -f .env ]; then
  cp .env.ornek .env
  yaz "[2/4] .env yoktu; .env.ornek'ten uretildi." "$SARI"
else
  yaz "[2/4] .env mevcut; eksik sirlar tamamlanacak." "$YESIL"
fi

if [ -z "$(oku KUTYAI_GIZLI_ANAHTAR)" ]; then
  doldur KUTYAI_GIZLI_ANAHTAR "$(base64url 48 dolgusuz)"
  yaz "      KUTYAI_GIZLI_ANAHTAR uretildi." "$SARI"
fi
if [ -z "$(oku KUTYAI_SIFRELEME_ANAHTARI)" ]; then
  # Fernet anahtari: 32 rastgele baytin urlsafe base64 hali (dolgulu).
  doldur KUTYAI_SIFRELEME_ANAHTARI "$(base64url 32)"
  yaz "      KUTYAI_SIFRELEME_ANAHTARI uretildi." "$SARI"
fi

PROFIL_ARG=()
case "$PROFIL" in
  postgres)
    if [ -z "$(oku KUTYAI_POSTGRES_PAROLA)" ]; then
      doldur KUTYAI_POSTGRES_PAROLA "$(base64url 24 dolgusuz)"
    fi
    KUTYAI_POSTGRES_KULLANICI="$(oku KUTYAI_POSTGRES_KULLANICI)"; KUTYAI_POSTGRES_KULLANICI="${KUTYAI_POSTGRES_KULLANICI:-kutyai}"
    KUTYAI_POSTGRES_VERITABANI="$(oku KUTYAI_POSTGRES_VERITABANI)"; KUTYAI_POSTGRES_VERITABANI="${KUTYAI_POSTGRES_VERITABANI:-kutyai}"
    KUTYAI_POSTGRES_PAROLA="$(oku KUTYAI_POSTGRES_PAROLA)"
    export KUTYAI_VERITABANI_URL="postgresql+asyncpg://${KUTYAI_POSTGRES_KULLANICI}:${KUTYAI_POSTGRES_PAROLA}@postgres:5432/${KUTYAI_POSTGRES_VERITABANI}"
    PROFIL_ARG=(--profile postgres)
    yaz "      PostgreSQL profili: KUTYAI_VERITABANI_URL=${KUTYAI_VERITABANI_URL}" "$SARI"
    ;;
  nginx)
    PROFIL_ARG=(--profile nginx)
    ;;
esac

# --- 3) Derleme ve kaldirma ---------------------------------------------------
DERLEME_ARG=()
if [ -n "$YENIDEN_DERLE" ]; then
  DERLEME_ARG=("$YENIDEN_DERLE")
fi

yaz "[3/4] Imajlar derleniyor ve servisler kaldiriliyor (ilk derleme uzun surebilir)..." "$MAVI"
docker compose ${PROFIL_ARG[@]+"${PROFIL_ARG[@]}"} up -d --build ${DERLEME_ARG[@]+"${DERLEME_ARG[@]}"}

# --- 4) Saglik beklemesi ------------------------------------------------------
bekle() { # adres, saniye, etiket
  local adres="$1" saniye="$2" etiket="$3" bitis=$((SECONDS + $2))
  while [ "$SECONDS" -lt "$bitis" ]; do
    if [ "$(curl -s -o /dev/null -w '%{http_code}' -L --max-time 5 "$adres" || true)" = "200" ]; then
      yaz "  [tamam] ${etiket} -> ${adres}" "$YESIL"
      return 0
    fi
    sleep 3
  done
  yaz "  [HATA ] ${etiket} saglikli olmadi: ${adres}" "$KIRMIZI"
  return 1
}

yaz "[4/4] Saglik bekleniyor..." "$MAVI"
SAGLIKLI=0
bekle "http://localhost:8000/api/v1/saglik" 180 "arkauc" || SAGLIKLI=1
bekle "http://localhost:3000/" 120 "onuc" || SAGLIKLI=1
bekle "http://localhost:3001/" 120 "yonetim_paneli" || SAGLIKLI=1
if [ "$PROFIL" = "nginx" ]; then
  bekle "http://localhost:8080/" 60 "nginx" || SAGLIKLI=1
fi

echo
if [ "$SAGLIKLI" -eq 0 ]; then
  yaz "KutyAI ayakta." "$YESIL"
else
  yaz "Bazi servisler saglikli degil; gunlukler icin: docker compose logs -f" "$SARI"
fi
echo
yaz "Erisim adresleri:" "$MAVI"
echo "  API            http://localhost:8000/api/v1/saglik"
echo "  API belge      http://localhost:8000/api/docs"
echo "  Son kullanici  http://localhost:3000"
echo "  Yonetim paneli http://localhost:3001"
if [ "$PROFIL" = "nginx" ]; then
  echo "  Tek giris      http://localhost:8080"
fi
echo
echo "Durum:      docker compose ps"
echo "Gunlukler:  docker compose logs -f <servis>"
echo "Durdurma:   docker compose down"
echo

exit "$SAGLIKLI"
