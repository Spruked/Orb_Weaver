# ISS Scale desktop widget

This is the compact Tauri 2/Rust desktop surface for the Interplanetary Stardate Syncrometer Scale. It stays always-on-top, can be dragged by its header, and polls the local ISS service for the four required representations: Epoch, Standard, Julian, and ISS.

## Run

Start the time service from the parent module:

```bash
cd ..
python -m iss_module.service
```

Then, with Rust/Cargo installed:

```bash
cd widget
npm install
npm run tauri:dev
```

For a distributable build, run `npm run tauri:build`.

The widget expects the service at `http://127.0.0.1:8000/api/time`.

## Automatic start and crash recovery

On Linux, install the user-level supervisor after building:

```bash
./scripts/install_linux_autostart.sh
```

It starts the widget after login/reboot and restarts it indefinitely after a crash. Remove it with `./scripts/uninstall_linux_autostart.sh`.
