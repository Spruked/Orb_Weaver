"""Customer-owned runtime. No factory checkout or factory API is required."""
from pathlib import Path
import argparse
import os


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run this site's Website ORB")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8787, type=int)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    os.environ["ORB_WEAVER_VAULT_ROOT"] = str(Path(__file__).resolve().parent / "runtime/vault_system")
    from backend.integrity import validate_payload
    manifest = validate_payload()
    from backend.skg.runtime import load_site_graph
    load_site_graph()
    if args.check:
        print(f"Validated {manifest['site_id']} / {manifest['source']['scan_id']} / {manifest['build_id']}")
    else:
        import uvicorn
        uvicorn.run("backend.app:app", host=args.host, port=args.port)
