---
name: rival-one
description: Executes high-performance trading workflows on Rival One via WebSocket. Use for market data, order management, and risk margin.
version: 0.1.0
author: hermes
license: MIT
metadata:
  hermes:
    tags: [trading, websocket, mcp, rival-one, market-data, orders]
    related_skills: []
prerequisites:
  env_vars: [RIVAL_ONE_API_TOKEN]
  commands: [python3]
---

# Rival One Trading Skill

Interact with the Rival One (formerly Rival Trading) platform via a WebSocket-based MCP server for low-latency, bidirectional communication.

## Setup

1. Set your API token:
   ```bash
   export RIVAL_ONE_API_TOKEN="your-token-here"
   ```
2. Install dependencies:
   ```bash
   pip install -r rivalone/requirements.txt
   ```
3. Run the MCP server:
   ```bash
   python rivalone/rival_one_mcp.py
   ```

## Workflow: Order Management

1. **Validation**: All `Quantity` and `Price` values must be cast as **floating point numbers**. Integer parsing causes server exceptions.
2. **Place Order**: Use `Send order (Type 2)` with symbol, side (Buy/Sell), quantity, and price.
3. **Monitor**: Watch `Order Status (Type 8)` messages for execution updates (fills, rejects, cancels).
4. **Modify**: Use `Revise order (Type 4)` for cancel-replace actions on live orders.
5. **Cancel**: Use `Cancel order (Type 6)` to cancel an open order.

### Example: Place a Limit Order

```python
result = await server.send_order(
    symbol="ESM5",
    side="Buy",
    quantity=10.0,   # MUST be float
    price=4500.50,   # MUST be float
    order_type=2     # Limit
)
```

## Workflow: Market Data

1. Use `Instrument search (Type 33)` to find the correct symbol.
2. Send `Market data (Type 0)` with `IncludeOptions: true` to begin the subscription.
3. Register a handler for incoming market data updates.

### Example: Subscribe to Market Data

```python
await server.subscribe_market_data("ESM5", include_options=True)

@server.on_message(MSG_MARKET_DATA)
async def on_market_data(msg):
    print(f"Bid: {msg.get('Bid')} Ask: {msg.get('Ask')}")
```

## Safety & Constraints

- **GroupName**: Assigned by Rival One. **NEVER** attempt to modify; unauthorized changes result in immediate session termination.
- **Heartbeat**: A `Ping (Type 26)` must be sent at least every 5 minutes to maintain the session. The server sends it every 4 minutes automatically.
- **Float Enforcement**: All price and quantity fields must be `float`. Using `int` triggers server-side exceptions.
- **Authentication**: Requires Bearer token in WebSocket header + Type 45 Authorize message after connection.

## Message Type Reference

See `references/message_types.md` for the full list of Rival One message types and their fields.
