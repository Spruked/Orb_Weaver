#!/usr/bin/env python3
"""Narrow Docker-bridge relay for the host-local Ollama HTTP service.

This is transport only. Provider selection and model policy remain in the ORB
inference gateway. The listener binds to the Docker host-gateway address and
forwards to Ollama's loopback listener; it is not a general network proxy.
"""

from __future__ import annotations

import asyncio
import os


LISTEN_HOST = os.getenv("OLLAMA_DOCKER_RELAY_HOST", "172.17.0.1")
LISTEN_PORT = int(os.getenv("OLLAMA_DOCKER_RELAY_PORT", "11435"))
TARGET_HOST = "127.0.0.1"
TARGET_PORT = 11434


async def pipe(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    try:
        while chunk := await reader.read(64 * 1024):
            writer.write(chunk)
            await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()


async def relay(client_reader: asyncio.StreamReader, client_writer: asyncio.StreamWriter) -> None:
    try:
        upstream_reader, upstream_writer = await asyncio.open_connection(TARGET_HOST, TARGET_PORT)
    except OSError:
        client_writer.close()
        await client_writer.wait_closed()
        return
    await asyncio.gather(
        pipe(client_reader, upstream_writer),
        pipe(upstream_reader, client_writer),
    )
    upstream_writer.close()
    await upstream_writer.wait_closed()


async def main() -> None:
    server = await asyncio.start_server(relay, LISTEN_HOST, LISTEN_PORT)
    addresses = ", ".join(str(sock.getsockname()) for sock in server.sockets or [])
    print(f"Ollama Docker bridge listening on {addresses}; forwarding to {TARGET_HOST}:{TARGET_PORT}", flush=True)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
