"""
Database Administration Commands for Ring4 SMS Bot
Provides admin commands for database backup management, protection status,
and recovery operations.
"""

import logging
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.protected_database import ProtectedDatabase
from src.database_protection import DatabaseProtectionError

logger = logging.getLogger(__name__)


class DatabaseAdminCommands:
    """Database administration commands for admins"""

    def __init__(self, protected_db: ProtectedDatabase):
        self.db = protected_db

    async def protection_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Show database protection status"""
        try:
            status = self.db.get_protection_status()

            if not status.get("protection_enabled", False):
                message = "⚠️ *Database Protection Status*\n\n"
                message += "🔴 *PROTECTION DISABLED*\n"
                message += "Database is running without protection!\n"
                message += "Data may be vulnerable to corruption and loss.\n\n"
                message += "Contact administrator to enable protection."
            else:
                message = "🛡️ *Database Protection Status*\n\n"
                message += f"✅ Protection: **Enabled**\n"
                message += f"📊 Database Valid: **{status.get('database_valid', 'Unknown')}**\n"
                message += f"🔄 Backup Service: **{'Running' if status.get('backup_service_running') else 'Stopped'}**\n"
                message += f"📁 Backup Directory: `{status.get('backup_dir', 'Unknown')}`\n"
                message += f"⏰ Backup Interval: **{status.get('backup_interval_hours', 0)} hours**\n"
                message += f"📦 Total Backups: **{status.get('total_backups', 0)}**\n"

                last_backup = status.get('last_backup')
                if last_backup:
                    message += f"🕒 Last Backup: `{last_backup}`\n"
                else:
                    message += "🕒 Last Backup: **Never**\n"

                next_backup = status.get('next_backup_eta')
                if next_backup:
                    if next_backup == "Soon":
                        message += "⏭️ Next Backup: **Soon**\n"
                    elif next_backup == "Overdue":
                        message += "⚠️ Next Backup: **Overdue**\n"
                    else:
                        message += f"⏭️ Next Backup: `{next_backup}`\n"

            keyboard = [
                [InlineKeyboardButton("🔄 Refresh Status",
                                      callback_data="db_status_refresh")],
                [InlineKeyboardButton(
                    "📋 List Backups", callback_data="db_list_backups")],
                [InlineKeyboardButton(
                    "🚨 Emergency Backup", callback_data="db_emergency_backup")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            if update.message:
                await update.message.reply_text(
                    message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )

        except Exception as e:
            logger.error(f"❌ Error getting protection status: {e}")
            if update.message:
                await update.message.reply_text(
                    f"❌ Error getting protection status: {str(e)}",
                    parse_mode='Markdown'
                )

    async def list_backups(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """List available database backups"""
        try:
            backups = self.db.get_backup_list()

            if not backups:
                message = "📦 *Database Backups*\n\n"
                message += "No backups found.\n"
                message += "Create a backup using the emergency backup button."
            else:
                message = f"📦 *Database Backups* ({len(backups)} found)\n\n"

                # Show max 10 backups
                for i, backup in enumerate(backups[:10], 1):
                    filename = backup.get('filename', 'Unknown')
                    size_mb = backup.get('size_mb', 0)
                    age_hours = backup.get('age_hours', 0)

                    if age_hours < 1:
                        age_str = f"{int(age_hours * 60)}m"
                    elif age_hours < 24:
                        age_str = f"{int(age_hours)}h"
                    else:
                        age_str = f"{int(age_hours / 24)}d"

                    message += f"{i}. `{filename}`\n"
                    message += f"   📏 Size: {size_mb:.1f}MB | 🕒 Age: {age_str}\n\n"

                if len(backups) > 10:
                    message += f"... and {len(backups) - 10} more backups"

            keyboard = [
                [InlineKeyboardButton(
                    "🔄 Refresh List", callback_data="db_list_backups")],
                [InlineKeyboardButton(
                    "🚨 Emergency Backup", callback_data="db_emergency_backup")],
                [InlineKeyboardButton(
                    "🏠 Protection Status", callback_data="db_status_refresh")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            if update.message:
                await update.message.reply_text(
                    message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            else:
                await update.callback_query.edit_message_text(
                    message,
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )

        except Exception as e:
            logger.error(f"❌ Error listing backups: {e}")
            error_message = f"❌ Error listing backups: {str(e)}"

            if update.message:
                await update.message.reply_text(error_message)
            else:
                await update.callback_query.answer(error_message, show_alert=True)

    async def create_emergency_backup(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Create an emergency backup immediately"""
        try:
            # Show progress message
            if update.callback_query:
                await update.callback_query.answer("Creating emergency backup...")
                message_to_edit = update.callback_query.message
            else:
                message_to_edit = await update.message.reply_text("🚨 Creating emergency backup...")

            # Create backup
            backup_path = self.db.emergency_backup()
            backup_filename = Path(backup_path).name
            backup_size = Path(backup_path).stat().st_size / \
                (1024 * 1024)  # Size in MB

            message = "✅ *Emergency Backup Created*\n\n"
            message += f"📁 File: `{backup_filename}`\n"
            message += f"📏 Size: {backup_size:.1f}MB\n"
            message += f"🕒 Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            message += "Backup created successfully and stored securely."

            keyboard = [
                [InlineKeyboardButton(
                    "📋 List All Backups", callback_data="db_list_backups")],
                [InlineKeyboardButton(
                    "🏠 Protection Status", callback_data="db_status_refresh")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await message_to_edit.edit_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

        except DatabaseProtectionError as e:
            error_message = f"❌ Protection Error: {str(e)}"
            logger.error(error_message)

            if update.callback_query:
                await update.callback_query.answer(error_message, show_alert=True)
            else:
                await update.message.reply_text(error_message)

        except Exception as e:
            error_message = f"❌ Backup creation failed: {str(e)}"
            logger.error(error_message)

            if update.callback_query:
                await update.callback_query.answer(error_message, show_alert=True)
            else:
                await update.message.reply_text(error_message)

    async def validate_database(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Validate database integrity"""
        try:
            is_valid = self.db.validate_database_integrity()

            if is_valid:
                message = "✅ *Database Integrity Check*\n\n"
                message += "Database is healthy and valid.\n"
                message += "No corruption detected."
            else:
                message = "⚠️ *Database Integrity Check*\n\n"
                message += "🔴 **CORRUPTION DETECTED**\n"
                message += "Database may be corrupted.\n\n"
                message += "Recommended actions:\n"
                message += "• Create emergency backup if possible\n"
                message += "• Consider restoring from recent backup\n"
                message += "• Contact technical support"

            keyboard = [
                [InlineKeyboardButton(
                    "🚨 Emergency Backup", callback_data="db_emergency_backup")],
                [InlineKeyboardButton(
                    "📋 List Backups", callback_data="db_list_backups")],
                [InlineKeyboardButton(
                    "🏠 Protection Status", callback_data="db_status_refresh")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )

        except Exception as e:
            logger.error(f"❌ Error validating database: {e}")
            await update.message.reply_text(
                f"❌ Error validating database: {str(e)}",
                parse_mode='Markdown'
            )

    async def manual_backup(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Create a manual backup with custom name"""
        try:
            # Extract backup name from command args
            backup_name = None
            if context.args:
                backup_name = "_".join(context.args)
                if not backup_name.endswith('.json'):
                    backup_name += '.json'

            backup_path = self.db.create_manual_backup(backup_name)
            backup_filename = Path(backup_path).name
            backup_size = Path(backup_path).stat().st_size / (1024 * 1024)

            message = "✅ *Manual Backup Created*\n\n"
            message += f"📁 File: `{backup_filename}`\n"
            message += f"📏 Size: {backup_size:.1f}MB\n"
            message += f"🕒 Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            message += "Backup created successfully."

            await update.message.reply_text(
                message,
                parse_mode='Markdown'
            )

        except DatabaseProtectionError as e:
            await update.message.reply_text(
                f"❌ Protection Error: {str(e)}",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"❌ Manual backup failed: {e}")
            await update.message.reply_text(
                f"❌ Manual backup failed: {str(e)}",
                parse_mode='Markdown'
            )

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle database admin callback queries"""
        query = update.callback_query
        await query.answer()

        if query.data == "db_status_refresh":
            # Update the message with fresh protection status
            await self.protection_status(update, context)

        elif query.data == "db_list_backups":
            await self.list_backups(update, context)

        elif query.data == "db_emergency_backup":
            await self.create_emergency_backup(update, context)

        else:
            await query.answer("Unknown command", show_alert=True)


def get_database_commands_help() -> str:
    """Get help text for database commands"""
    return """
🛡️ *Database Protection Commands*

*Admin Only:*
• `/db_status` - Show database protection status
• `/db_backups` - List available backups
• `/db_backup [name]` - Create manual backup
• `/db_validate` - Check database integrity
• `/db_emergency` - Create emergency backup

*Features:*
• ✅ Automated backup every 3 days
• 🔒 Write-locking prevents corruption
• 🔄 Automatic recovery from backups
• 📦 Multiple backup retention
• 🚨 Emergency backup capabilities

*Backup Storage:*
Backups are stored in `data/backups/` directory and cannot be accidentally deleted when uploading to GitHub.
"""
