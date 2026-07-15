# Orb Weaver MCP Server Slot

Copy the Orb Weaver MCP server files into this folder so the local relay can run:

```text
.runtime/rdrive_mpc_server/orb_mcp_server.py
```

`tools/start_orb_mcp_host_relay.sh` prefers this repo-local copy when it exists,
then falls back to `/mnt/r/mpc_server` for the desktop ORB copy.

Only run one relay per port. Multiple MCP server copies are fine; multiple
active relays on `8765` are not.
