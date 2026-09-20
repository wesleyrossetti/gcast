{{- define "gcast-server.fullname" -}}
{{- .Release.Name -}}
{{- end -}}

{{- define "gcast-server.labels" -}}
app.kubernetes.io/name: {{ include "gcast-server.fullname" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "gcast-server.postgresHost" -}}
{{ include "gcast-server.fullname" . }}-postgres
{{- end -}}

{{- define "gcast-server.databaseUrl" -}}
postgresql+asyncpg://{{ .Values.postgres.user }}:{{ .Values.postgres.password }}@{{ include "gcast-server.postgresHost" . }}:5432/{{ .Values.postgres.database }}
{{- end -}}
