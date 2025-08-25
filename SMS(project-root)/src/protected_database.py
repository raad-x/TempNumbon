"""
Enhanced Database with Protection System Integration
Replaces the standard Database class with bulletproof protection.
"""

import os
import logging
import json
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from tinydb import TinyDB

from src.database_protection import DatabaseProtectionService, DatabaseProtectionError

logger = logging.getLogger(__name__)


class ProtectedDatabase:
    """
    Enhanced database wrapper with integrated protection system.
    Drop-in replacement for the standard Database class with bulletproof protection.
    """

    def __init__(self, database_path: str = "data/ring4_database.json", enable_protection: bool = True):
        """
        Initialize protected database with integrated protection service.

        Args:
            database_path: Path to the database file
            enable_protection: Whether to enable protection features (default: True)
        """
        self.database_path = database_path
        self.enable_protection = enable_protection

        # Initialize database structure first
        self._initialize_database()

        # Create TinyDB instance for backward compatibility
        self.db = TinyDB(database_path)

        # Initialize protection service if enabled
        if self.enable_protection:
            try:
                self.protection_service = DatabaseProtectionService(
                    database_path=database_path,
                    backup_interval_hours=72,  # 3 days as requested
                    max_backups=10  # Keep 10 backups (30 days worth)
                )
                logger.info(
                    "Database protection service initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize protection service: {e}")
                self.protection_service = None
        else:
            self.protection_service = None

        logger.info(f"Protected database initialized: {database_path}")

    def _initialize_database(self):
        """Initialize database with default structure if it doesn't exist."""
        if not os.path.exists(self.database_path):
            os.makedirs(os.path.dirname(self.database_path), exist_ok=True)

            default_structure = {
                "wallets": {},
                "orders": {},
                "transactions": {},
                "deposits": {},
                "refunds": {}
            }

            with open(self.database_path, 'w') as f:
                json.dump(default_structure, f, indent=2)

            logger.info("Database initialized with default structure")

    def _read_database(self) -> Dict[str, Any]:
        """Safely read database with protection."""
        try:
            if self.protection_service:
                # Use protection service for safe reading with validation
                if self.protection_service._validate_database_integrity():
                    with open(self.database_path, 'r') as f:
                        return json.load(f)
                else:
                    # Attempt recovery if integrity check fails
                    if self.protection_service._attempt_recovery():
                        with open(self.database_path, 'r') as f:
                            return json.load(f)
                    else:
                        logger.error("Database corrupted and recovery failed")
                        return {"wallets": {}, "orders": {}, "transactions": {}, "deposits": {}, "refunds": {}}
            else:
                # Fallback to direct reading
                with open(self.database_path, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Database read error: {e}")
            return {"wallets": {}, "orders": {}, "transactions": {}, "deposits": {}, "refunds": {}}

    def _write_database(self, data: Dict[str, Any]):
        """Safely write database with protection."""
        try:
            if self.protection_service:
                # Use protection service for safe writing with atomic operations
                with self.protection_service.write_lock():
                    self.protection_service._write_database_atomic(data)
            else:
                # Fallback to direct writing
                with open(self.database_path, 'w') as f:
                    json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Database write error: {e}")
            raise DatabaseProtectionError(f"Failed to write database: {e}")

    # Wallet Management Methods
    def create_wallet(self, user_id: int) -> bool:
        """Create a new wallet for user."""
        try:
            data = self._read_database()

            if str(user_id) not in data["wallets"]:
                data["wallets"][str(user_id)] = {
                    "user_id": user_id,
                    "balance": 0.0,
                    "created_at": self._get_timestamp()
                }
                self._write_database(data)
                logger.info(f"Wallet created for user {user_id}")
                return True

            return False
        except Exception as e:
            logger.error(f"Error creating wallet for user {user_id}: {e}")
            return False

    def get_wallet(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get wallet information for user."""
        try:
            data = self._read_database()
            return data["wallets"].get(str(user_id))
        except Exception as e:
            logger.error(f"Error getting wallet for user {user_id}: {e}")
            return None

    def update_balance(self, user_id: int, new_balance: float) -> bool:
        """Update user's wallet balance."""
        try:
            data = self._read_database()

            if str(user_id) in data["wallets"]:
                data["wallets"][str(user_id)]["balance"] = new_balance
                data["wallets"][str(
                    user_id)]["updated_at"] = self._get_timestamp()
                self._write_database(data)
                logger.info(
                    f"Balance updated for user {user_id}: {new_balance}")
                return True

            return False
        except Exception as e:
            logger.error(f"Error updating balance for user {user_id}: {e}")
            return False

    def add_balance(self, user_id: int, amount: float) -> bool:
        """Add amount to user's balance."""
        try:
            wallet = self.get_wallet(user_id)
            if wallet:
                new_balance = wallet["balance"] + amount
                return self.update_balance(user_id, new_balance)
            return False
        except Exception as e:
            logger.error(f"Error adding balance for user {user_id}: {e}")
            return False

    def subtract_balance(self, user_id: int, amount: float) -> bool:
        """Subtract amount from user's balance."""
        try:
            wallet = self.get_wallet(user_id)
            if wallet and wallet["balance"] >= amount:
                new_balance = wallet["balance"] - amount
                return self.update_balance(user_id, new_balance)
            return False
        except Exception as e:
            logger.error(f"Error subtracting balance for user {user_id}: {e}")
            return False

    # Order Management Methods
    def create_order(self, user_id: int, order_data: Dict[str, Any]) -> Optional[str]:
        """Create a new order."""
        try:
            data = self._read_database()

            order_id = order_data.get(
                'order_id', f"ORDER_{user_id}_{len(data['orders']) + 1}")

            data["orders"][order_id] = {
                "user_id": user_id,
                "status": "pending",
                "created_at": self._get_timestamp(),
                **order_data
            }

            self._write_database(data)
            logger.info(f"Order created: {order_id}")
            return order_id
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return None

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order by ID."""
        try:
            data = self._read_database()
            return data["orders"].get(order_id)
        except Exception as e:
            logger.error(f"Error getting order {order_id}: {e}")
            return None

    def update_order_status(self, order_id: str, status: str, sms_code: Optional[str] = None) -> bool:
        """Update order status."""
        try:
            data = self._read_database()

            if order_id in data["orders"]:
                data["orders"][order_id]["status"] = status
                data["orders"][order_id]["updated_at"] = self._get_timestamp()

                if sms_code:
                    data["orders"][order_id]["sms_code"] = sms_code

                self._write_database(data)
                logger.info(f"Order {order_id} status updated: {status}")
                return True

            return False
        except Exception as e:
            logger.error(f"Error updating order {order_id}: {e}")
            return False

    def get_user_orders(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all orders for a user."""
        try:
            data = self._read_database()
            user_orders = []

            for order_id, order in data["orders"].items():
                if order.get("user_id") == user_id:
                    order_copy = order.copy()
                    order_copy["order_id"] = order_id
                    user_orders.append(order_copy)

            return user_orders
        except Exception as e:
            logger.error(f"Error getting orders for user {user_id}: {e}")
            return []

    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        return self.update_order_status(order_id, "cancelled")

    # Transaction Management Methods
    def record_transaction(self, user_id: int, transaction_type: str, amount: float, description: str = "") -> Optional[str]:
        """Record a transaction."""
        try:
            data = self._read_database()

            transaction_id = f"TXN_{user_id}_{len(data['transactions']) + 1}"

            data["transactions"][transaction_id] = {
                "user_id": user_id,
                "type": transaction_type,
                "amount": amount,
                "description": description,
                "timestamp": self._get_timestamp()
            }

            self._write_database(data)
            logger.info(f"Transaction recorded: {transaction_id}")
            return transaction_id
        except Exception as e:
            logger.error(f"Error recording transaction: {e}")
            return None

    def get_user_transactions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all transactions for a user."""
        try:
            data = self._read_database()
            user_transactions = []

            for txn_id, txn in data["transactions"].items():
                if txn.get("user_id") == user_id:
                    txn_copy = txn.copy()
                    txn_copy["transaction_id"] = txn_id
                    user_transactions.append(txn_copy)

            return user_transactions
        except Exception as e:
            logger.error(f"Error getting transactions for user {user_id}: {e}")
            return []

    # Deposit Management Methods
    def record_deposit(self, user_id: int, amount: float, payment_method: str, transaction_id: str) -> Optional[str]:
        """Record a deposit."""
        try:
            data = self._read_database()

            deposit_id = f"DEP_{user_id}_{len(data['deposits']) + 1}"

            data["deposits"][deposit_id] = {
                "user_id": user_id,
                "amount": amount,
                "payment_method": payment_method,
                "transaction_id": transaction_id,
                "status": "pending",
                "timestamp": self._get_timestamp()
            }

            self._write_database(data)
            logger.info(f"Deposit recorded: {deposit_id}")
            return deposit_id
        except Exception as e:
            logger.error(f"Error recording deposit: {e}")
            return None

    def approve_deposit(self, deposit_id: str) -> bool:
        """Approve a deposit."""
        try:
            data = self._read_database()

            if deposit_id in data["deposits"]:
                deposit = data["deposits"][deposit_id]
                data["deposits"][deposit_id]["status"] = "approved"
                data["deposits"][deposit_id]["approved_at"] = self._get_timestamp()

                # Add to user's balance
                user_id = deposit["user_id"]
                amount = deposit["amount"]
                self.add_balance(user_id, amount)

                # Record transaction
                self.record_transaction(
                    user_id, "deposit", amount, f"Deposit approved: {deposit_id}")

                self._write_database(data)
                logger.info(f"Deposit approved: {deposit_id}")
                return True

            return False
        except Exception as e:
            logger.error(f"Error approving deposit {deposit_id}: {e}")
            return False

    # Refund Management Methods
    def create_refund(self, user_id: int, order_id: str, amount: float, reason: str) -> Optional[str]:
        """Create a refund."""
        try:
            data = self._read_database()

            refund_id = f"REF_{user_id}_{len(data['refunds']) + 1}"

            data["refunds"][refund_id] = {
                "user_id": user_id,
                "order_id": order_id,
                "amount": amount,
                "reason": reason,
                "status": "pending",
                "timestamp": self._get_timestamp()
            }

            self._write_database(data)
            logger.info(f"Refund created: {refund_id}")
            return refund_id
        except Exception as e:
            logger.error(f"Error creating refund: {e}")
            return None

    def process_refund(self, refund_id: str) -> bool:
        """Process a refund."""
        try:
            data = self._read_database()

            if refund_id in data["refunds"]:
                refund = data["refunds"][refund_id]
                data["refunds"][refund_id]["status"] = "processed"
                data["refunds"][refund_id]["processed_at"] = self._get_timestamp()

                # Add to user's balance
                user_id = refund["user_id"]
                amount = refund["amount"]
                self.add_balance(user_id, amount)

                # Record transaction
                self.record_transaction(
                    user_id, "refund", amount, f"Refund processed: {refund_id}")

                self._write_database(data)
                logger.info(f"Refund processed: {refund_id}")
                return True

            return False
        except Exception as e:
            logger.error(f"Error processing refund {refund_id}: {e}")
            return False

    # Protection System Methods
    def create_manual_backup(self, description: str = "") -> Optional[str]:
        """Create a manual backup."""
        if self.protection_service:
            backup_path = self.protection_service.create_backup(
                f"manual_{description}")
            return str(backup_path)
        return None

    def emergency_backup(self) -> Optional[str]:
        """Create an emergency backup."""
        if self.protection_service:
            backup_path = self.protection_service.emergency_backup()
            return str(backup_path)
        return None

    def get_backup_list(self) -> List[Dict[str, Any]]:
        """Get list of available backups."""
        if self.protection_service:
            return self.protection_service.get_backup_info()
        return []

    def validate_database_integrity(self) -> bool:
        """Validate database integrity."""
        if self.protection_service:
            return self.protection_service._validate_database_integrity()
        return True

    def get_protection_status(self) -> Dict[str, Any]:
        """Get protection status."""
        if self.protection_service:
            return self.protection_service.get_protection_status()
        return {"protection_enabled": False}

    def restore_from_backup(self, backup_filename: str) -> bool:
        """Restore database from backup."""
        if self.protection_service:
            return self.protection_service.restore_from_backup(backup_filename)
        return False

    # Utility Methods
    def _get_timestamp(self) -> str:
        """Get current timestamp string."""
        from datetime import datetime
        return datetime.now().isoformat()

    def close(self):
        """Close database and cleanup."""
        if hasattr(self, 'db') and self.db:
            self.db.close()
        if self.protection_service:
            self.protection_service.stop_backup_service()
        logger.info("Protected database closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Backward compatibility alias
Database = ProtectedDatabase
