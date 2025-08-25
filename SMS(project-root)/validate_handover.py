#!/usr/bin/env python3
"""
Ring4 SMS Bot - Client Handover Validation
Validates that all components are ready for client delivery
"""

import os
import sys
from pathlib import Path


def validate_project():
    """Validate project is ready for client handover"""
    print("🔍 Ring4 SMS Bot - Client Handover Validation")
    print("=" * 55)

    issues = []
    warnings = []

    # Check essential files
    essential_files = [
        'main.py',
        'README.md',
        'CLIENT_HANDOVER.md',
        'client_setup.sh',
        'start_bot.sh',
        'restart_bot.sh',
        '.env.example',
        '.gitignore',
        'requirements.txt',
        'src/database_protection.py',
        'src/protected_database.py',
        'src/database_admin.py',
        'src/wallet_system.py',
        'src/smspool_api.py',
        'src/config.py'
    ]

    print("\n📁 Checking Essential Files...")
    for file in essential_files:
        if os.path.exists(file):
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file}")
            issues.append(f"Missing essential file: {file}")

    # Check directories
    essential_dirs = ['src', 'data', 'logs', 'data/backups']

    print("\n📂 Checking Directories...")
    for directory in essential_dirs:
        if os.path.exists(directory):
            print(f"   ✅ {directory}/")
        else:
            print(f"   ❌ {directory}/")
            issues.append(f"Missing directory: {directory}")

    # Check permissions
    executable_files = ['client_setup.sh', 'start_bot.sh', 'restart_bot.sh']

    print("\n🔐 Checking Permissions...")
    for file in executable_files:
        if os.path.exists(file):
            if os.access(file, os.X_OK):
                print(f"   ✅ {file} (executable)")
            else:
                print(f"   ⚠️ {file} (not executable)")
                warnings.append(f"File not executable: {file}")
        else:
            print(f"   ❌ {file} (missing)")

    # Check for sensitive files that shouldn't be included
    sensitive_files = ['.env']

    print("\n🔒 Checking for Sensitive Files...")
    for file in sensitive_files:
        if os.path.exists(file):
            print(f"   ⚠️ {file} (should be excluded from delivery)")
            warnings.append(f"Sensitive file present: {file}")
        else:
            print(f"   ✅ {file} (properly excluded)")

    # Check for unnecessary files
    unnecessary_patterns = ['*.pyc', '__pycache__',
                            '*.log', '.DS_Store', '*.tmp']

    print("\n🧹 Checking for Unnecessary Files...")
    found_unnecessary = False
    for pattern in unnecessary_patterns:
        import glob
        matches = glob.glob(f"**/{pattern}", recursive=True)
        if matches:
            found_unnecessary = True
            for match in matches:
                print(f"   ⚠️ {match}")
                warnings.append(f"Unnecessary file: {match}")

    if not found_unnecessary:
        print("   ✅ No unnecessary files found")

    # Test imports
    print("\n🧪 Testing Core Imports...")
    try:
        sys.path.insert(0, '.')

        from src.database_protection import DatabaseProtectionService
        print("   ✅ database_protection")

        from src.protected_database import ProtectedDatabase
        print("   ✅ protected_database")

        from src.database_admin import DatabaseAdminCommands
        print("   ✅ database_admin")

        from src.wallet_system import WalletSystem
        print("   ✅ wallet_system")

        from src.smspool_api import SMSPoolAPI
        print("   ✅ smspool_api")

        import src.config
        print("   ✅ config")

    except Exception as e:
        print(f"   ❌ Import error: {e}")
        issues.append(f"Import error: {e}")

    # Summary
    print("\n" + "=" * 55)
    print("📋 VALIDATION SUMMARY")
    print("=" * 55)

    if not issues and not warnings:
        print("🎉 PERFECT! Project is 100% ready for client handover!")
        print("✅ All essential files present")
        print("✅ All imports working")
        print("✅ No unnecessary files")
        print("✅ Proper permissions set")
        return True

    if issues:
        print(f"❌ ISSUES FOUND ({len(issues)}):")
        for issue in issues:
            print(f"   • {issue}")

    if warnings:
        print(f"⚠️ WARNINGS ({len(warnings)}):")
        for warning in warnings:
            print(f"   • {warning}")

    if not issues:
        print("✅ No critical issues - project ready for delivery!")
        return True
    else:
        print("❌ Critical issues must be resolved before delivery!")
        return False


if __name__ == "__main__":
    success = validate_project()
    sys.exit(0 if success else 1)
