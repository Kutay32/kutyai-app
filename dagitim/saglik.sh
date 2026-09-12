#!/usr/bin/env bash
# KutyAI servislerinin sagligini yoklar: arkauc (API), onuc, yonetim_paneli.
# Uc servis de saglikliysa cikis kodu 0, degilse 1 doner.
#
#   ./saglik.sh
set -uo pipefail

cd "$(dirname "$0")"

if [ -t 1 ]; then
  KIRMIZI=$'\033[31m'; YESIL=$'\033[32m'; SARI=$'\033[33m'; MAVI=$'\033[36m'; DUZ=$'\033[0m'
else
  KIRMIZI=""; YESIL=""; SARI=""; MAVI=""; DUZ=""
fi

echo
echo "${MAVI}KutyAI saglik kontrolu${DUZ}"
echo "${MAVI}======================${DUZ}"

HATA=0

yokla() { # ad, adres
  local ad="$1" adres="$2" kod govde not
  govde="$(curl -sL --max-time 5 -w '\n%{http_code}' "$adres" 2>/dev/null || true)"
  kod="$(printf '%s' "$govde" | tail -n 1)"
  govde="$(printf '%s' "$govde" | sed '$d')"

  case "$kod" in
    200)
      not="yanit veriyor"
      if [ "$ad" = "arkauc" ]; then
        local durum surum
        durum="$(printf '%s' "$govde" | sed -n 's/.*"durum":"\([^"]*\)".*/\1/p')"
        surum="$(printf '%s' "$govde" | sed -n 's/.*"surum":"\([^"]*\)".*/\1/p')"
        [ -n "$durum" ] && not="uygulama: ${durum}, surum ${surum:-?}"
      fi
      printf '  %s[TAMAM]%s %-16s %s  HTTP 200  (%s)\n' "$YESIL" "$DUZ" "$ad" "$adres" "$not"
      ;;
    *)
      if [ -z "$kod" ] || [ "$kod" = "000" ]; then
        kod="-"
        not="erisilemedi"
      else
        not="beklenmeyen durum kodu"
      fi
      printf '  %s[HATA ]%s %-16s %s  HTTP %s  (%s)\n' "$KIRMIZI" "$DUZ" "$ad" "$adres" "$kod" "$not"
      HATA=1
      ;;
  esac
}

yokla "arkauc"         "http://localhost:8000/api/v1/saglik"
yokla "onuc"           "http://localhost:3000/"
yokla "yonetim_paneli" "http://localhost:3001/"

echo
echo "${MAVI}Konteyner durumu:${DUZ}"
if command -v docker >/dev/null 2>&1 && docker compose ps >/dev/null 2>&1; then
  docker compose ps --format $'  {{.Service}}\t{{.State}}\t{{.Health}}' 2>/dev/null || echo "  (docker compose ps okunamadi)"
else
  echo "  (docker daemon erisilemiyor)"
fi

echo
if [ "$HATA" -ne 0 ]; then
  echo "${KIRMIZI}SONUC: bazi servisler saglikli degil.${DUZ}"
  echo "${SARI}Gunlukler: docker compose logs -f <servis>${DUZ}"
  exit 1
fi

echo "${YESIL}SONUC: tum servisler saglikli.${DUZ}"
exit 0
