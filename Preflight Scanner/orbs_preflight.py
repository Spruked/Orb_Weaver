#!/usr/bin/env python3
"""
orbs_preflight.py
Entry point for standalone ORB preflight site scan.
Usage: python3 orbs_preflight.py --root <url> --output <dir>
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from typing import Any, Dict

# ---------------------------------------------------------------------------
# Optional import — compile-safe fallback
# ---------------------------------------------------------------------------
try:
    from preflight_site_scan import PreflightScanner
except ImportError:
    print("ERROR: preflight_site_scan.py not found in Python path.", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logger = logging.getLogger("orbs_preflight")
if not logger.handlers:
    _handler = logging.FileHandler("scanner.log")
    _handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    ))
    logger.addHandler(_handler)
    logger.setLevel(logging.INFO)


# ---------------------------------------------------------------------------
# Terminal output helpers
# ---------------------------------------------------------------------------

def _fmt_bool(value: bool) -> str:
    return "yes" if value else "no"


def _fmt_opt(value: Any) -> str:
    if value is None:
        return "none"
    if isinstance(value, bool):
        return _fmt_bool(value)
    if isinstance(value, list):
        if not value:
            return "none"
        return ", ".join(str(v) for v in value)
    return str(value)


def print_summary(report: Dict[str, Any]) -> None:
    """Print human-readable preflight summary to terminal."""
    detected = report.get("detected", {})
    site_url = report.get("site_url", "unknown")

    print()
    print("=" * 60)
    print("  ORBS Preflight Site Scan")
    print(f"  Site: {site_url}")
    print("=" * 60)
    print()
    print("Detected:")
    print(f"  Existing chat widget:       {_fmt_bool(detected.get('existing_chat_widget', False))}")
    print(f"  External assistant API:     {_fmt_opt(detected.get('external_assistant_endpoint'))}")
    print(f"  Framework:                  {_fmt_opt(detected.get('cms_framework'))}")
    print(f"  Contact form:               {_fmt_bool(detected.get('has_contact_form', False))}")
    print(f"  Auth/login pages:           {_fmt_bool(detected.get('has_auth_pages', False))}")
    print(f"  Products/services:          {_fmt_bool(detected.get('has_products', False))}")
    print(f"  E-commerce checkout:        {_fmt_bool(detected.get('has_checkout', False))}")
    print(f"  Booking system:             {_fmt_bool(detected.get('has_booking', False))}")
    print(f"  Blog/news:                  {_fmt_bool(detected.get('has_blog', False))}")
    print(f"  PDFs/downloads:             {_fmt_bool(detected.get('has_pdfs', False))}")

    robots_txt = detected.get("robots_txt", False)
    robots_count = detected.get("robots_disallow_count", 0)
    print(f"  robots.txt:                 {'found' if robots_txt else 'not found'}")

    sitemap_present = detected.get("sitemap_xml", False)
    sitemap_count = detected.get("sitemap_url_count", 0)
    sitemap_str = f"found ({sitemap_count} URLs)" if sitemap_present else "not found"
    print(f"  sitemap.xml:                {sitemap_str}")

    broken = detected.get("broken_links", [])
    print(f"  Broken links:               {len(broken)} found")

    placeholders = detected.get("placeholder_pages", [])
    print(f"  Placeholder pages:          {len(placeholders)} found")

    third_party = detected.get("third_party_scripts", [])
    print(f"  Third-party scripts:        {_fmt_opt(third_party)}")

    external = detected.get("external_domains", [])
    print(f"  External domains:           {_fmt_opt(external)}")
    print()

    mode = report.get("recommended_install_mode", "unknown")
    print("Recommended install mode:")
    print(f"  {mode}")
    print()

    steps = report.get("required_custom_steps", [])
    print("Required custom steps:")
    if steps:
        for step in steps:
            print(f"  - {step}")
    else:
        print("  (none)")
    print()

    warnings = report.get("warnings", [])
    print("Warnings:")
    if warnings:
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("  (none)")
    print()

    output_dir = report.get("_output_dir", "")
    report_path = os.path.join(output_dir, "site_preflight_report.json")
    print(f"Report saved: {report_path}")
    print("=" * 60)
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> int:
    parser = argparse.ArgumentParser(
        description="ORB Preflight Site Scanner — lightweight reconnaissance before SSI install."
    )
    parser.add_argument(
        "--root",
        required=True,
        help="Root URL of the target site (e.g., https://example.com).",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output directory for site_preflight_report.json.",
    )
    args = parser.parse_args()

    root_url = args.root.strip()
    output_dir = os.path.abspath(args.output.strip())

    if not root_url.startswith(("http://", "https://")):
        root_url = "https://" + root_url

    logger.info("Starting ORBS preflight scan for %s -> %s", root_url, output_dir)

    try:
        scanner = PreflightScanner(root_url=root_url, output_dir=output_dir)
        report = await scanner.scan()
        report["_output_dir"] = output_dir  # stash for print_summary
        print_summary(report)
        logger.info("Preflight scan completed successfully.")
        return 0
    except Exception as exc:
        logger.error("Preflight scan failed: %s", str(exc), exc_info=True)
        print(f"ERROR: Preflight scan failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
