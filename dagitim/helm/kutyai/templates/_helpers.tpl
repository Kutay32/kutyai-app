{{/*
KutyAI ortak Helm yardımcıları.
Etiket sözleşmesi (Kubernetes önerileri):
  app.kubernetes.io/name        -> chart adı (nameOverride ile ezilebilir)
  app.kubernetes.io/instance    -> Release adı
  app.kubernetes.io/component   -> arka-uc | onuc | panel | yapilandirma | goc | ingress
  app.kubernetes.io/version     -> Chart.appVersion
  app.kubernetes.io/managed-by  -> Release.Service
  app.kubernetes.io/part-of     -> kutyai
  helm.sh/chart                 -> <chart>-<sürüm>

Etiket yardımcıları kök bağlam + bileşen adı bekler:
  {{ include "kutyai.etiketler" (dict "kok" $ "bilesen" "onuc") }}
*/}}

{{/* Chart adı. */}}
{{- define "kutyai.ad" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Kaynak adı kökü (ör. kutyai-kutyai -> release adı). */}}
{{- define "kutyai.tamAd" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $ad := include "kutyai.ad" . -}}
{{- if contains $ad .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $ad | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/* Kaynakların yazılacağı ad alanı. */}}
{{- define "kutyai.namespace" -}}
{{- default .Release.Namespace .Values.namespace.name -}}
{{- end -}}

{{/* Helm chart etiketi. */}}
{{- define "kutyai.chartEtiketi" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* Seçici etiketleri: Deployment/Service/HPA eşleşmesi için sabit küme
     (sürüm etiketi EKLENMEZ; aksi halde yükseltmede seçici değişir). */}}
{{- define "kutyai.seciciler" -}}
app.kubernetes.io/name: {{ include "kutyai.ad" .kok }}
app.kubernetes.io/instance: {{ .kok.Release.Name }}
app.kubernetes.io/component: {{ .bilesen }}
{{- end -}}

{{/* Tam etiket kümesi (metadata.labels + pod template etiketleri). */}}
{{- define "kutyai.etiketler" -}}
{{ include "kutyai.seciciler" . }}
helm.sh/chart: {{ include "kutyai.chartEtiketi" .kok }}
{{- if .kok.Chart.AppVersion }}
app.kubernetes.io/version: {{ .kok.Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .kok.Release.Service }}
app.kubernetes.io/part-of: kutyai
{{- end -}}

{{/* Bileşenin kaynak adı: <kök>-<bilesen>. Geçersiz bileşen adında hata verir. */}}
{{- define "kutyai.bilesenAdi" -}}
{{- if not (has .bilesen (list "arka-uc" "onuc" "panel")) -}}
{{- fail (printf "geçersiz bileşen adı %q (arka-uc | onuc | panel olmalı)" .bilesen) -}}
{{- end -}}
{{- printf "%s-%s" (include "kutyai.tamAd" .kok) .bilesen -}}
{{- end -}}

{{/* Sır kaynağının adı (existingSecret verilmişse o). */}}
{{- define "kutyai.secretAd" -}}
{{- default (include "kutyai.tamAd" .) .Values.secrets.existingSecret -}}
{{- end -}}

{{/* ConfigMap adı. */}}
{{- define "kutyai.configmapAd" -}}
{{- printf "%s-yapilandirma" (include "kutyai.tamAd" .) -}}
{{- end -}}

{{/* ServiceAccount adı. */}}
{{- define "kutyai.serviceAccountAd" -}}
{{- default (include "kutyai.tamAd" .) .Values.serviceAccount.name -}}
{{- end -}}

{{/* İmaj referansı: repository:tag (tag boşsa appVersion). */}}
{{- define "kutyai.imaj" -}}
{{- printf "%s:%s" .repository (.tag | default .appVersion) -}}
{{- end -}}

{{/* Bir sırrın mevcut Secret'taki değeri (varsa), aksi halde boş dize.
     Yükseltmede üretilen sırların KORUNMASINI sağlar.
     {{ include "kutyai.mevcutSir" (dict "ns" $ns "ad" $ad "anahtar" "KUTYAI_X") }} */}}
{{- define "kutyai.mevcutSir" -}}
{{- $secret := lookup "v1" "Secret" .ns .ad -}}
{{- if $secret -}}
{{- $deger := index $secret.data .anahtar | default "" -}}
{{- if $deger -}}
{{- $deger | b64dec -}}
{{- end -}}
{{- end -}}
{{- end -}}
