# API Documentation - PX Platform

<div align="center">

**API Reference** | **Versão**: 1.0.0 | **Última Atualização**: 19/10/2025

[![API](https://img.shields.io/badge/API-REST-blue)](https://api.px-platform.com)
[![OpenAPI](https://img.shields.io/badge/OpenAPI-3.0-green)](https://api.px-platform.com/docs)
[![DATAMETRIA](https://img.shields.io/badge/DATAMETRIA-Standards-blue)](https://github.com/datametria/standards)

[🔑 Autenticação](#-autenticação) • [📊 Events API](#-events-api) • [🧠 Insights API](#-insights-api) • [⚡ Real-time API](#-real-time-api)

</div>

---

## 📋 Índice

- [🔑 Autenticação](#-autenticação)
- [📊 Events API](#-events-api)
- [🧠 Insights API](#-insights-api)
- [⚡ Real-time API](#-real-time-api)
- [🎯 Experiments API](#-experiments-api)
- [👥 Users API](#-users-api)
- [📈 Analytics API](#-analytics-api)
- [🔧 Admin API](#-admin-api)

---

## 🔑 Autenticação

### API Keys

```http
POST /api/v1/auth/token
Content-Type: application/json

{
  "api_key": "px_live_1234567890abcdef",
  "project_id": "proj_uuid_here"
}
```

**Response**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "project_id": "proj_uuid_here",
  "tenant_id": "tenant_uuid_here"
}
```

### Headers Obrigatórios

```http
Authorization: Bearer {access_token}
Content-Type: application/json
X-PX-Project-ID: {project_id}
```

### Rate Limiting

| Tier | Limite | Headers de Resposta |
|------|--------|-------------------|
| **Free** | 1,000/hour | `X-RateLimit-Limit: 1000` |
| **Pro** | 10,000/hour | `X-RateLimit-Remaining: 9999` |
| **Enterprise** | Unlimited | `X-RateLimit-Reset: 1640995200` |

---

## 📊 Events API

### Ingerir Eventos (Batch)

```http
POST /api/v1/events/batch
Authorization: Bearer {token}
Content-Type: application/json
Content-Encoding: gzip

{
  "events": [
    {
      "event": "page_view",
      "user_id": "user_uuid",
      "session_id": "session_uuid",
      "timestamp": "2024-01-01T12:00:00Z",
      "properties": {
        "page": "/signup",
        "referrer": "https://google.com",
        "utm_source": "google",
        "utm_campaign": "brand"
      }
    },
    {
      "event": "signup_step_completed",
      "user_id": "user_uuid",
      "session_id": "session_uuid",
      "timestamp": "2024-01-01T12:01:30Z",
      "properties": {
        "step": 1,
        "method": "email",
        "form_duration": 90
      }
    }
  ]
}
```

**Response** (`202 Accepted`):
```json
{
  "success": true,
  "events_received": 2,
  "processing_id": "batch_uuid",
  "estimated_processing_time": "5s"
}
```

### Buscar Eventos

```http
GET /api/v1/events?user_id={uuid}&limit=100&offset=0
Authorization: Bearer {token}
```

**Query Parameters**:
| Parâmetro | Tipo | Descrição | Exemplo |
|-----------|------|-----------|---------|
| `user_id` | UUID | Filtrar por usuário | `user_123` |
| `session_id` | UUID | Filtrar por sessão | `session_456` |
| `event` | String | Tipo de evento | `signup_completed` |
| `start_date` | ISO Date | Data inicial | `2024-01-01T00:00:00Z` |
| `end_date` | ISO Date | Data final | `2024-01-31T23:59:59Z` |
| `limit` | Integer | Máximo 1000 | `100` |
| `offset` | Integer | Paginação | `0` |

**Response**:
```json
{
  "events": [
    {
      "id": "event_uuid",
      "event": "signup_completed",
      "user_id": "user_uuid",
      "session_id": "session_uuid",
      "timestamp": "2024-01-01T12:05:00Z",
      "properties": {
        "plan": "pro",
        "trial_days": 14
      },
      "enriched_data": {
        "geo_country": "BR",
        "geo_city": "São Paulo",
        "device_type": "desktop",
        "browser": "Chrome"
      }
    }
  ],
  "total": 1,
  "has_more": false,
  "next_offset": null
}
```

### Eventos Customizados

```http
POST /api/v1/events/custom
Authorization: Bearer {token}

{
  "event": "feature_used",
  "user_id": "user_uuid",
  "properties": {
    "feature_name": "advanced_analytics",
    "usage_duration": 300,
    "success": true
  }
}
```

---

## 🧠 Insights API

### Gerar Insights com IA

```http
POST /api/v1/insights/generate
Authorization: Bearer {token}

{
  "type": "friction_detection",
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-01-31"
  },
  "filters": {
    "funnel": "signup_flow",
    "segment": "new_users"
  }
}
```

**Response**:
```json
{
  "insight_id": "insight_uuid",
  "type": "friction_detection",
  "status": "completed",
  "generated_at": "2024-01-01T12:00:00Z",
  "results": {
    "friction_points": [
      {
        "step": "email_verification",
        "drop_off_rate": 0.35,
        "impact_score": 0.89,
        "affected_users": 1250,
        "revenue_impact": 15000,
        "ai_recommendation": {
          "action": "Simplify email verification process",
          "confidence": 0.92,
          "estimated_improvement": "+12% conversion"
        }
      }
    ],
    "correlations": [
      {
        "factor": "mobile_users",
        "correlation": 0.78,
        "insight": "Mobile users have 78% higher drop-off rate"
      }
    ]
  }
}
```

### Listar Insights

```http
GET /api/v1/insights?type=friction_detection&status=completed
Authorization: Bearer {token}
```

**Response**:
```json
{
  "insights": [
    {
      "id": "insight_uuid",
      "type": "friction_detection",
      "status": "completed",
      "priority": "high",
      "created_at": "2024-01-01T12:00:00Z",
      "summary": "Found 3 critical friction points in signup flow"
    }
  ],
  "total": 1
}
```

### Feedback de Insight

```http
POST /api/v1/insights/{insight_id}/feedback
Authorization: Bearer {token}

{
  "rating": 5,
  "implemented": true,
  "impact_observed": "+8% conversion",
  "comments": "Great recommendation, easy to implement"
}
```

---

## ⚡ Real-time API

### WebSocket Connection

```javascript
const ws = new WebSocket('wss://api.px-platform.com/v1/realtime');

ws.onopen = function() {
  // Autenticar
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'bearer_token_here',
    project_id: 'project_uuid'
  }));
  
  // Subscrever eventos
  ws.send(JSON.stringify({
    type: 'subscribe',
    channels: ['events', 'insights', 'experiments']
  }));
};

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'event':
      console.log('New event:', data.payload);
      break;
    case 'insight':
      console.log('New insight:', data.payload);
      break;
    case 'experiment_result':
      console.log('Experiment update:', data.payload);
      break;
  }
};
```

### Server-Sent Events (SSE)

```http
GET /api/v1/stream/events
Authorization: Bearer {token}
Accept: text/event-stream
```

**Response Stream**:
```
data: {"type": "event", "event": "signup_completed", "user_id": "user_123"}

data: {"type": "insight", "insight_id": "insight_456", "priority": "high"}

data: {"type": "experiment", "experiment_id": "exp_789", "variant": "B", "result": "winner"}
```

---

## 🎯 Experiments API

### Criar Experimento

```http
POST /api/v1/experiments
Authorization: Bearer {token}

{
  "name": "Checkout Flow Optimization",
  "description": "Test simplified vs detailed checkout",
  "type": "a_b_test",
  "variants": [
    {
      "name": "control",
      "traffic_allocation": 0.5,
      "config": {
        "checkout_type": "detailed"
      }
    },
    {
      "name": "simplified",
      "traffic_allocation": 0.5,
      "config": {
        "checkout_type": "simplified"
      }
    }
  ],
  "target_metric": "conversion_rate",
  "duration_days": 14,
  "min_sample_size": 1000
}
```

**Response**:
```json
{
  "experiment_id": "exp_uuid",
  "status": "draft",
  "created_at": "2024-01-01T12:00:00Z",
  "estimated_duration": "14 days",
  "statistical_power": 0.8
}
```

### Obter Variante para Usuário

```http
GET /api/v1/experiments/{experiment_id}/variant?user_id={user_uuid}
Authorization: Bearer {token}
```

**Response**:
```json
{
  "experiment_id": "exp_uuid",
  "variant": "simplified",
  "config": {
    "checkout_type": "simplified"
  },
  "tracking_id": "tracking_uuid"
}
```

### Resultados do Experimento

```http
GET /api/v1/experiments/{experiment_id}/results
Authorization: Bearer {token}
```

**Response**:
```json
{
  "experiment_id": "exp_uuid",
  "status": "running",
  "duration_elapsed": 7,
  "participants": 2500,
  "results": {
    "control": {
      "participants": 1250,
      "conversions": 125,
      "conversion_rate": 0.10,
      "confidence_interval": [0.08, 0.12]
    },
    "simplified": {
      "participants": 1250,
      "conversions": 175,
      "conversion_rate": 0.14,
      "confidence_interval": [0.12, 0.16]
    }
  },
  "statistical_significance": 0.95,
  "winner": "simplified",
  "lift": 0.04,
  "ai_recommendation": "Deploy simplified variant to 100% of users"
}
```

---

## 👥 Users API

### Perfil do Usuário

```http
GET /api/v1/users/{user_id}
Authorization: Bearer {token}
```

**Response**:
```json
{
  "user_id": "user_uuid",
  "first_seen": "2024-01-01T10:00:00Z",
  "last_seen": "2024-01-01T15:30:00Z",
  "total_sessions": 5,
  "total_events": 47,
  "properties": {
    "email": "user@example.com",
    "plan": "pro",
    "signup_date": "2024-01-01"
  },
  "segments": ["high_value", "power_user"],
  "lifetime_value": 299.99,
  "churn_probability": 0.15
}
```

### Timeline do Usuário

```http
GET /api/v1/users/{user_id}/timeline?limit=50
Authorization: Bearer {token}
```

**Response**:
```json
{
  "user_id": "user_uuid",
  "timeline": [
    {
      "timestamp": "2024-01-01T15:30:00Z",
      "type": "event",
      "event": "feature_used",
      "properties": {
        "feature": "analytics_dashboard"
      }
    },
    {
      "timestamp": "2024-01-01T15:25:00Z",
      "type": "insight",
      "insight": "User showing high engagement patterns",
      "confidence": 0.89
    }
  ]
}
```

### Segmentação

```http
POST /api/v1/users/segment
Authorization: Bearer {token}

{
  "name": "High Value Users",
  "criteria": {
    "lifetime_value": {"gte": 100},
    "last_seen": {"gte": "7d"},
    "events_count": {"gte": 10}
  }
}
```

---

## 📈 Analytics API

### Funnels

```http
POST /api/v1/analytics/funnels
Authorization: Bearer {token}

{
  "name": "Signup Funnel",
  "steps": [
    {"event": "page_view", "properties": {"page": "/signup"}},
    {"event": "signup_started"},
    {"event": "email_verified"},
    {"event": "signup_completed"}
  ],
  "date_range": {
    "start": "2024-01-01",
    "end": "2024-01-31"
  }
}
```

**Response**:
```json
{
  "funnel_id": "funnel_uuid",
  "steps": [
    {
      "step": 1,
      "event": "page_view",
      "users": 10000,
      "conversion_rate": 1.0,
      "drop_off": 0
    },
    {
      "step": 2,
      "event": "signup_started",
      "users": 7500,
      "conversion_rate": 0.75,
      "drop_off": 2500
    },
    {
      "step": 3,
      "event": "email_verified",
      "users": 6000,
      "conversion_rate": 0.80,
      "drop_off": 1500
    },
    {
      "step": 4,
      "event": "signup_completed",
      "users": 5400,
      "conversion_rate": 0.90,
      "drop_off": 600
    }
  ],
  "overall_conversion": 0.54,
  "ai_insights": [
    "Biggest drop-off at email verification step",
    "Mobile users have 23% lower conversion"
  ]
}
```

### Métricas em Tempo Real

```http
GET /api/v1/analytics/metrics/realtime
Authorization: Bearer {token}
```

**Response**:
```json
{
  "timestamp": "2024-01-01T15:30:00Z",
  "active_users": 1250,
  "events_per_minute": 450,
  "conversion_rate_1h": 0.12,
  "top_events": [
    {"event": "page_view", "count": 180},
    {"event": "click", "count": 120},
    {"event": "signup_started", "count": 25}
  ],
  "friction_alerts": [
    {
      "type": "high_drop_off",
      "location": "checkout_step_2",
      "severity": "high"
    }
  ]
}
```

---

## 🔧 Admin API

### Projetos

```http
POST /api/v1/admin/projects
Authorization: Bearer {admin_token}

{
  "name": "E-commerce Platform",
  "domain": "shop.example.com",
  "plan": "pro",
  "settings": {
    "data_retention_days": 365,
    "pii_masking": true,
    "real_time_processing": true
  }
}
```

### Configuração de Eventos

```http
POST /api/v1/admin/projects/{project_id}/event-schemas
Authorization: Bearer {admin_token}

{
  "event": "purchase_completed",
  "schema": {
    "type": "object",
    "required": ["user_id", "order_id", "amount"],
    "properties": {
      "user_id": {"type": "string"},
      "order_id": {"type": "string"},
      "amount": {"type": "number", "minimum": 0},
      "currency": {"type": "string", "default": "USD"}
    }
  }
}
```

---

## 📊 Códigos de Status

| Código | Descrição | Exemplo |
|--------|-----------|---------|
| `200` | Sucesso | Dados retornados |
| `201` | Criado | Recurso criado |
| `202` | Aceito | Processamento assíncrono |
| `400` | Requisição inválida | Dados malformados |
| `401` | Não autorizado | Token inválido |
| `403` | Proibido | Sem permissão |
| `404` | Não encontrado | Recurso inexistente |
| `429` | Rate limit | Muitas requisições |
| `500` | Erro interno | Erro do servidor |

---

## 🔗 SDKs Oficiais

### JavaScript/TypeScript

```bash
npm install @px-platform/sdk
```

```javascript
import PX from '@px-platform/sdk'

PX.init({
  apiKey: 'px_live_...',
  projectId: 'proj_...'
})

PX.track('event_name', properties)
```

### Python

```bash
pip install px-platform-python
```

```python
from px_platform import PXClient

client = PXClient(api_key='px_live_...')
client.track('event_name', properties)
```

### Node.js

```bash
npm install @px-platform/node
```

```javascript
const PX = require('@px-platform/node')

const client = new PX({
  apiKey: 'px_live_...',
  projectId: 'proj_...'
})

await client.track('event_name', properties)
```

---

## 🧪 Ambiente de Testes

### Base URLs

| Ambiente | URL | Propósito |
|----------|-----|-----------|
| **Development** | `https://api-dev.px-platform.com` | Desenvolvimento |
| **Staging** | `https://api-staging.px-platform.com` | Testes |
| **Production** | `https://api.px-platform.com` | Produção |

### API Keys de Teste

```
# Desenvolvimento
px_test_1234567890abcdef

# Staging  
px_staging_1234567890abcdef

# Produção
px_live_1234567890abcdef
```

---

<div align="center">

**API Documentation mantida por Lila Rodrigues**

**Última atualização**: 19/10/2025 | **Versão**: 1.0.0

---

**Dúvidas sobre a API?** Entre em contato via [Discord](https://discord.gg/kKYGmCC3)

</div>