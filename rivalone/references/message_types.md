# Rival One Message Types Reference

Detailed reference for all supported Rival One WebSocket message types.

## Connection & Session

| Type | Name      | Direction       | Description                                      |
|------|-----------|-----------------|--------------------------------------------------|
| 26   | Ping      | Client → Server | Heartbeat. Must be sent every 4-5 minutes.       |
| 45   | Authorize | Client → Server | Authenticate with API token after WS connection. |

### Type 45 — Authorize

```json
{
  "Type": 45,
  "RequestId": "<uuid>",
  "Token": "<api-token>"
}
```

### Type 26 — Ping

```json
{
  "Type": 26
}
```

## Order Management

| Type | Name         | Direction       | Description                          |
|------|--------------|-----------------|--------------------------------------|
| 2    | Send Order   | Client → Server | Place a new order.                   |
| 4    | Revise Order | Client → Server | Cancel-replace an existing order.    |
| 6    | Cancel Order | Client → Server | Cancel an open order.                |
| 8    | Order Status | Server → Client | Execution report (fill, reject, etc).|

### Type 2 — Send Order

```json
{
  "Type": 2,
  "RequestId": "<uuid>",
  "Symbol": "ESM5",
  "Side": "Buy",
  "Quantity": 10.0,
  "Price": 4500.50,
  "OrderType": 2
}
```

**Fields:**
- `Symbol` (string): Instrument symbol.
- `Side` (string): `"Buy"` or `"Sell"`.
- `Quantity` (float): **Must be float.** Integer values cause exceptions.
- `Price` (float): **Must be float.** Limit price for the order.
- `OrderType` (int): `1` = Market, `2` = Limit.

### Type 4 — Revise Order

```json
{
  "Type": 4,
  "RequestId": "<uuid>",
  "OrderId": "<order-id>",
  "Quantity": 5.0,
  "Price": 4501.00
}
```

**Fields:**
- `OrderId` (string): ID of the order to revise.
- `Quantity` (float, optional): New quantity.
- `Price` (float, optional): New price.

### Type 6 — Cancel Order

```json
{
  "Type": 6,
  "RequestId": "<uuid>",
  "OrderId": "<order-id>"
}
```

### Type 8 — Order Status (Server Response)

```json
{
  "Type": 8,
  "OrderId": "<order-id>",
  "Status": "Filled",
  "FilledQuantity": 10.0,
  "AveragePrice": 4500.50
}
```

**Status Values:** `New`, `PartiallyFilled`, `Filled`, `Cancelled`, `Rejected`.

## Market Data

| Type | Name              | Direction       | Description                         |
|------|-------------------|-----------------|-------------------------------------|
| 0    | Market Data       | Bidirectional   | Subscribe (C→S) / Updates (S→C).   |
| 33   | Instrument Search | Client → Server | Search for instruments by query.    |

### Type 0 — Market Data Subscribe

```json
{
  "Type": 0,
  "RequestId": "<uuid>",
  "Symbol": "ESM5",
  "IncludeOptions": true
}
```

### Type 0 — Market Data Update (Server Push)

```json
{
  "Type": 0,
  "Symbol": "ESM5",
  "Bid": 4500.25,
  "Ask": 4500.50,
  "Last": 4500.375,
  "Volume": 125000
}
```

### Type 33 — Instrument Search

```json
{
  "Type": 33,
  "RequestId": "<uuid>",
  "Query": "ES"
}
```

**Response:**
```json
{
  "Type": 33,
  "RequestId": "<uuid>",
  "Results": [
    {"Symbol": "ESM5", "Name": "E-mini S&P 500 Jun 2025", "Exchange": "CME"},
    {"Symbol": "ESU5", "Name": "E-mini S&P 500 Sep 2025", "Exchange": "CME"}
  ]
}
```
