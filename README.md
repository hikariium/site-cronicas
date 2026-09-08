# API de votação para Render

API em Flask para gerar tokens, validar acesso e registrar votos para apuração.

## Endpoints

- `GET /health`
- `POST /api/tokens`
- `POST /api/register-token`
- `POST /api/tokens/validate`
- `POST /api/votes`
- `GET /api/results`

## Exemplo de uso

### Gerar token

```bash
curl -X POST https://SEU-SERVICE.onrender.com/api/tokens \
  -H "Content-Type: application/json" \
  -d '{"length":18,"upper":true,"lower":true,"numbers":true,"symbols":false}'
```

### Validar token

```bash
curl -X POST https://SEU-SERVICE.onrender.com/api/tokens/validate \
  -H "Content-Type: application/json" \
  -d '{"token":"ABC123"}'
```

### Registrar voto

```bash
curl -X POST https://SEU-SERVICE.onrender.com/api/votes \
  -H "Content-Type: application/json" \
  -d '{"token":"ABC123","presidencia":"13","governador":"1399"}'
```

### Consultar apuração

```bash
curl https://SEU-SERVICE.onrender.com/api/results
```

## Deploy no Render

1. Crie um novo Web Service no Render.
2. Conecte este repositório.
3. Use o comando de start padrão do arquivo `render.yaml`.
4. Em `Environment Variables`, deixe `DATA_DIR=/data` para manter os dados persistentes.

> Em serviços gratuitos do Render, arquivos salvos em `/data` são persistentes em um volume anexado ao serviço.

## Observação sobre o frontend

O site no Neocities pode chamar esta API usando `fetch()` em endpoints como:

- `/api/tokens`
- `/api/tokens/validate`
- `/api/votes`
- `/api/results`

Como os domínios são diferentes, a API precisa aceitar CORS.

