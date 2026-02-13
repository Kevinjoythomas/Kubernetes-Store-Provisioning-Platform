{{/*
Expand the name of the chart.
*/}}
{{- define "store.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "store.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "store.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "store.labels" -}}
helm.sh/chart: {{ include "store.chart" . }}
{{ include "store.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
platform.urumi.io/store-id: {{ .Values.storeId | quote }}
platform.urumi.io/store-type: {{ .Values.storeType | quote }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "store.selectorLabels" -}}
app.kubernetes.io/name: {{ include "store.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
MariaDB labels
*/}}
{{- define "store.mariadb.labels" -}}
{{ include "store.labels" . }}
app.kubernetes.io/component: mariadb
{{- end }}

{{/*
MariaDB selector labels
*/}}
{{- define "store.mariadb.selectorLabels" -}}
{{ include "store.selectorLabels" . }}
app.kubernetes.io/component: mariadb
{{- end }}

{{/*
WordPress labels
*/}}
{{- define "store.wordpress.labels" -}}
{{ include "store.labels" . }}
app.kubernetes.io/component: wordpress
{{- end }}

{{/*
WordPress selector labels
*/}}
{{- define "store.wordpress.selectorLabels" -}}
{{ include "store.selectorLabels" . }}
app.kubernetes.io/component: wordpress
{{- end }}

{{/*
Namespace name for this store
*/}}
{{- define "store.namespace" -}}
{{- printf "store-%s" .Values.storeId }}
{{- end }}

{{/*
Store hostname (used for ingress)
*/}}
{{- define "store.hostname" -}}
{{- printf "%s.%s" .Values.storeId .Values.baseDomain }}
{{- end }}

{{/*
WordPress admin email
*/}}
{{- define "store.wordpress.adminEmail" -}}
{{- if .Values.wordpress.admin.email }}
{{- .Values.wordpress.admin.email }}
{{- else }}
{{- printf "admin@%s.%s" .Values.storeId .Values.baseDomain }}
{{- end }}
{{- end }}

{{/*
Validate required values
*/}}
{{- define "store.validateValues" -}}
{{- if not .Values.storeId }}
{{- fail "storeId is required. Please set .Values.storeId" }}
{{- end }}
{{- if not (regexMatch "^[a-z0-9]([-a-z0-9]*[a-z0-9])?$" .Values.storeId) }}
{{- fail "storeId must be a valid DNS label (lowercase alphanumeric and hyphens only, must start and end with alphanumeric)" }}
{{- end }}
{{- if not .Values.baseDomain }}
{{- fail "baseDomain is required. Please set .Values.baseDomain" }}
{{- end }}
{{- end }}
