#!/usr/bin/env python3
"""Interactive setup wizard for SiteOwlQA user configuration.

Run this once to create ~/.siteowlqa/config.json with your sensitive data.

Usage:
    python -m siteowlqa.setup_config
"""

import sys

from siteowlqa.user_config import create_user_config_interactive


if __name__ == "__main__":
    try:
        create_user_config_interactive()
        print("\nSetup complete! You can now run the pipeline:")
        print("  python main.py")
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
