"""
Rival One MCP-WebSocket Server

A production-grade MCP server that connects to the Rival One trading platform
via WebSocket for low-latency, bidirectional communication. Supports order
management, market data subscriptions, and instrument search.

Authentication: Bearer token in WebSocket header + Type 45 Authorize message.
Heartbeat: Type 26 Ping every 4 minutes to maintain session.
"""

import asyncio
import json
import logging
import os
import uuid

import websockets

logger = logging.getLogger(__name__)

# Rival One Endpoints
SIM_ENDPOINT = "wss://sim-api.rivalsystems.cloud:50443"
PROD_ENDPOINT = "wss://api.rivalsystems.cloud:50443"

# Heartbeat interval in seconds (4 minutes)
HEARTBEAT_INTERVAL = 240

# Rival One Message Types
MSG_MARKET_DATA = 0
MSG_SEND_ORDER = 2
MSG_REVISE_ORDER = 4
MSG_CANCEL_ORDER = 6
MSG_ORDER_STATUS = 8
MSG_PING = 26
MSG_INSTRUMENT_SEARCH = 33
MSG_AUTHORIZE = 45


class RivalOneMCPServer:
    """MCP-WebSocket server for Rival One trading platform."""

    def __init__(self, api_token: str, endpoint: str = SIM_ENDPOINT):
        self.api_token = api_token
        self.endpoint = endpoint
        self.ws = None
        self._heartbeat_task = None
        self._listener_task = None
        self._handlers = {}
        self._pending_requests = {}

    async def connect(self):
        """Connect to Rival One and authenticate."""
        headers = {"Authorization": f"Bearer {self.api_token}"}
        self.ws = await websockets.connect(self.endpoint, extra_headers=headers)
        logger.info("WebSocket connected to %s", self.endpoint)

        # Authenticate with Type 45 Authorize message
        request_id = str(uuid.uuid4())
        auth_msg = {
            "Type": MSG_AUTHORIZE,
            "RequestId": request_id,
            "Token": self.api_token,
        }
        await self.ws.send(json.dumps(auth_msg))
        logger.info("Authorize message sent (RequestId: %s)", request_id)

        # Start heartbeat and listener
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._listener_task = asyncio.create_task(self._listener_loop())

    async def disconnect(self):
        """Gracefully close the connection."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        if self._listener_task:
            self._listener_task.cancel()
        if self.ws:
            await self.ws.close()
            logger.info("WebSocket disconnected")

    async def _heartbeat_loop(self):
        """Send Type 26 Ping every 4 minutes to maintain the session."""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                await self.ws.send(json.dumps({"Type": MSG_PING}))
                logger.debug("Heartbeat ping sent")
        except asyncio.CancelledError:
            pass

    async def _listener_loop(self):
        """Listen for incoming messages and dispatch to handlers."""
        try:
            async for raw_msg in self.ws:
                msg = json.loads(raw_msg)
                msg_type = msg.get("Type")

                # Resolve pending request futures
                request_id = msg.get("RequestId")
                if request_id and request_id in self._pending_requests:
                    self._pending_requests[request_id].set_result(msg)

                # Dispatch to registered handlers
                if msg_type in self._handlers:
                    for handler in self._handlers[msg_type]:
                        asyncio.create_task(handler(msg))

                logger.debug("Received message Type=%s", msg_type)
        except websockets.ConnectionClosed as e:
            logger.warning("WebSocket connection closed: %s", e)
        except asyncio.CancelledError:
            pass

    def on_message(self, msg_type: int):
        """Decorator to register a handler for a specific message type."""
        def decorator(func):
            self._handlers.setdefault(msg_type, []).append(func)
            return func
        return decorator

    async def _send_and_wait(self, msg: dict, timeout: float = 10.0) -> dict:
        """Send a message and wait for a response with the same RequestId."""
        request_id = msg.get("RequestId", str(uuid.uuid4()))
        msg["RequestId"] = request_id

        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future

        await self.ws.send(json.dumps(msg))

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            self._pending_requests.pop(request_id, None)

    # ── MCP Tools ──────────────────────────────────────────────────────

    async def send_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        order_type: int = 2,
    ) -> dict:
        """
        Place a new order on Rival One.

        IMPORTANT: Quantity and Price MUST be floating point numbers.
        Integer values will cause server exceptions.

        Args:
            symbol: Instrument symbol (e.g. "ESM5").
            side: "Buy" or "Sell".
            quantity: Order quantity (float).
            price: Limit price (float).
            order_type: 2=Limit (default), 1=Market.

        Returns:
            Server acknowledgment message.
        """
        order_msg = {
            "Type": MSG_SEND_ORDER,
            "RequestId": str(uuid.uuid4()),
            "Symbol": symbol,
            "Side": side,
            "Quantity": float(quantity),
            "Price": float(price),
            "OrderType": order_type,
        }
        return await self._send_and_wait(order_msg)

    async def revise_order(
        self,
        order_id: str,
        quantity: float = None,
        price: float = None,
    ) -> dict:
        """
        Revise (cancel-replace) an existing order.

        Args:
            order_id: The ID of the order to revise.
            quantity: New quantity (float, optional).
            price: New price (float, optional).

        Returns:
            Server acknowledgment message.
        """
        revise_msg = {
            "Type": MSG_REVISE_ORDER,
            "RequestId": str(uuid.uuid4()),
            "OrderId": order_id,
        }
        if quantity is not None:
            revise_msg["Quantity"] = float(quantity)
        if price is not None:
            revise_msg["Price"] = float(price)
        return await self._send_and_wait(revise_msg)

    async def cancel_order(self, order_id: str) -> dict:
        """
        Cancel an existing order.

        Args:
            order_id: The ID of the order to cancel.

        Returns:
            Server acknowledgment message.
        """
        cancel_msg = {
            "Type": MSG_CANCEL_ORDER,
            "RequestId": str(uuid.uuid4()),
            "OrderId": order_id,
        }
        return await self._send_and_wait(cancel_msg)

    async def search_instruments(self, query: str) -> dict:
        """
        Search for instruments by symbol or name.

        Args:
            query: Search term (e.g. "ES" for E-mini S&P futures).

        Returns:
            Instrument search results.
        """
        search_msg = {
            "Type": MSG_INSTRUMENT_SEARCH,
            "RequestId": str(uuid.uuid4()),
            "Query": query,
        }
        return await self._send_and_wait(search_msg)

    async def subscribe_market_data(
        self,
        symbol: str,
        include_options: bool = False,
    ) -> dict:
        """
        Subscribe to real-time market data for a symbol.

        Args:
            symbol: Instrument symbol.
            include_options: Whether to include options chain data.

        Returns:
            Subscription acknowledgment. Market data updates will arrive
            via the on_message(MSG_MARKET_DATA) handler.
        """
        md_msg = {
            "Type": MSG_MARKET_DATA,
            "RequestId": str(uuid.uuid4()),
            "Symbol": symbol,
            "IncludeOptions": include_options,
        }
        return await self._send_and_wait(md_msg)


async def main():
    """Example usage of the Rival One MCP server."""
    api_token = os.environ.get("RIVAL_ONE_API_TOKEN")
    if not api_token:
        logger.error("RIVAL_ONE_API_TOKEN environment variable not set")
        return

    server = RivalOneMCPServer(api_token=api_token)

    # Register a handler for order status updates
    @server.on_message(MSG_ORDER_STATUS)
    async def on_order_status(msg):
        logger.info("Order status update: %s", json.dumps(msg, indent=2))

    # Register a handler for market data updates
    @server.on_message(MSG_MARKET_DATA)
    async def on_market_data(msg):
        logger.info("Market data: %s", json.dumps(msg, indent=2))

    try:
        await server.connect()

        # Search for an instrument
        results = await server.search_instruments("ES")
        logger.info("Instrument search results: %s", json.dumps(results, indent=2))

        # Keep running to receive events
        await asyncio.Future()
    except KeyboardInterrupt:
        pass
    finally:
        await server.disconnect()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
