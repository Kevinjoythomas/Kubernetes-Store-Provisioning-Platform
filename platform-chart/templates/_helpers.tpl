{{/*
Expand the name of the chart.
*/}}
{{- define "platform.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "platform.fullname" -}}
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
{{- define "platform.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Platform namespace
*/}}
{{- define "platform.namespace" -}}
{{- .Values.platformNamespace | default .Release.Namespace }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "platform.labels" -}}
helm.sh/chart: {{ include "platform.chart" . }}
{{ include "platform.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: store-platform
{{- end }}

{{/*
Selector labels
*/}}
{{- define "platform.selectorLabels" -}}
app.kubernetes.io/name: {{ include "platform.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
API labels
*/}}
{{- define "platform.api.labels" -}}
{{ include "platform.labels" . }}
app.kubernetes.io/component: api
{{- end }}

{{/*
API selector labels
*/}}
{{- define "platform.api.selectorLabels" -}}
{{ include "platform.selectorLabels" . }}
app.kubernetes.io/component: api
{{- end }}

{{/*
Dashboard labels
*/}}
{{- define "platform.dashboard.labels" -}}
{{ include "platform.labels" . }}
app.kubernetes.io/component: dashboard
{{- end }}

{{/*
Dashboard selector labels
*/}}
{{- define "platform.dashboard.selectorLabels" -}}
{{ include "platform.selectorLabels" . }}
app.kubernetes.io/component: dashboard
{{- end }}

{{/*
Controller labels
*/}}
{{- define "platform.controller.labels" -}}
{{ include "platform.labels" . }}
app.kubernetes.io/component: controller
{{- end }}

{{/*
Controller selector labels
*/}}
{{- define "platform.controller.selectorLabels" -}}
{{ include "platform.selectorLabels" . }}
app.kubernetes.io/component: controller
{{- end }}

{{/*
Create the name of the controller service account to use
*/}}
{{- define "platform.controller.serviceAccountName" -}}
{{- if .Values.controller.serviceAccount.create }}
{{- default "store-controller" .Values.controller.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.controller.serviceAccount.name }}
{{- end }}
{{- end }}
