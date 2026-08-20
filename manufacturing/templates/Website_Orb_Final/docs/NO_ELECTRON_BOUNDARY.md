# No Electron Boundary

The Website ORB package does not ship an Electron app.

Allowed:

- A DockStation adapter interface.
- Calls to a separately configured local MCP/Dock relay.
- Clear unavailable status when DockStation is not configured.

Not allowed inside this package:

- Electron main process.
- Electron preload runtime.
- Desktop window lifecycle.
- Local machine control by default.

