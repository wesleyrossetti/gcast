# gcast-server — Helm Chart

Deploy do backend multi-tenant do Chromecast Manager (`saas/server`) em Kubernetes,
com Postgres embutido no próprio chart e Ingress via Traefik.

O `saas/agent` **não** faz parte deste chart — ele precisa rodar na rede local onde
estão os Chromecasts (`docker run --network host ...`, veja a tela "Agentes" no
próprio dashboard depois do deploy).

## Pré-requisitos

1. Namespace já criado (`gcast` neste projeto).
2. Um secret de pull para o GitHub Container Registry (só necessário se o pacote
   `ghcr.io/wesleyrossetti/gcast-server` for privado):
   ```bash
   kubectl -n gcast create secret docker-registry ghcr-pull-secret \
     --docker-server=ghcr.io \
     --docker-username=<seu usuário do GitHub> \
     --docker-password=<Personal Access Token com escopo read:packages>
   ```

## Instalação

Gere valores para os dois segredos obrigatórios (nunca commitar os valores reais):

```bash
SECRET_KEY=$(openssl rand -hex 32)
PG_PASSWORD=$(openssl rand -hex 16)

helm install gcast-server ./saas/server/chart/gcast-server \
  -n gcast \
  --set secretKey="$SECRET_KEY" \
  --set postgres.password="$PG_PASSWORD"
```

Guarde `$PG_PASSWORD` em um cofre de senhas — ela é necessária em qualquer `helm upgrade`
futuro (o Helm não lê de volta o valor já aplicado no cluster).

## Verificar

```bash
kubectl -n gcast get pods,svc,ingress
curl -H "Host: gcast.wmanti.com.br" http://<IP externo do Traefik>/login
```

## TLS (opcional)

Se o cluster tiver cert-manager com um `ClusterIssuer` configurado, ajuste em
`values.yaml`:

```yaml
ingress:
  tls:
    enabled: true
    secretName: gcast-server-tls
    clusterIssuer: letsencrypt-prod
```

e descomente a annotation correspondente em `templates/ingress.yaml`.

## Atualizar a imagem

```bash
helm upgrade gcast-server ./saas/server/chart/gcast-server -n gcast \
  --set secretKey="$SECRET_KEY" \
  --set postgres.password="$PG_PASSWORD" \
  --set image.tag=<nova tag>
```
