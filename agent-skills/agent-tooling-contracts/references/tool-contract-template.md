# Template Contratto Tool

## Tool: <nome>

### Scopo

Breve descrizione di cosa fa e cosa non fa questo tool.

### Schema Input (stile JSON Schema)

```json
{
  "type": "object",
  "required": ["request_id"],
  "properties": {
    "request_id": {"type": "string"},
    "...": {}
  },
  "additionalProperties": false
}
```

### Schema Output

```json
{
  "type": "object",
  "required": ["status", "data"],
  "properties": {
    "status": {"type": "string", "enum": ["ok", "error"]},
    "data": {"type": "object"},
    "confidence": {"type": "number", "minimum": 0, "maximum": 1}
  }
}
```

### Schema Errore

```json
{
  "type": "object",
  "required": ["error_code", "message", "retriable"],
  "properties": {
    "error_code": {"type": "string"},
    "message": {"type": "string"},
    "retriable": {"type": "boolean"}
  }
}
```

### Policy Operativa

- Timeout:
- Max retry:
- Backoff strategy:
- Chiave idempotenza:

### Esempi Chiamata

- Richiesta valida + risposta valida
- Richiesta non valida + errore validazione
- Timeout + comportamento retry
