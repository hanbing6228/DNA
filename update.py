#!/usr/bin/env python3
"""DNA v2.1 Update Script - overwrites templates and web_api_v2.py"""
import shutil
from pathlib import Path

BASE = Path(__file__).parent

# Copy new files
shutil.copy(BASE / "index.html", BASE / "templates" / "index.html")
print("✅ Updated templates/index.html")

shutil.copy(BASE / "web_api_v2.py", BASE / "web_api_v2.py")
print("✅ Updated web_api_v2.py")

shutil.copy(BASE / "import_clinvar.py", BASE / "pipeline" / "import_clinvar.py")
print("✅ Updated pipeline/import_clinvar.py")

print("\n🎉 Update complete! Run: bash launch.sh")
