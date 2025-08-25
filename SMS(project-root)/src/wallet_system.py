"""
Wallet System for Ring4 SMS Bot
Handles user balance management, deposits, withdrawals, and transaction history
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from tinydb import Query

logger = logging.getLogger(__name__)


class WalletSystem:
    """
    Advanced Wallet System for Ring4 SMS Bot

    Features:
    - User balance management
    - Minimum deposit requirement ($1)
    - Maximum deposit limits ($1000)
    - Automatic service deduction
    - Refund processing
    - Transaction history
    - Admin approval workflow
    """

    MIN_DEPOSIT_USD = 1.00
    MAX_DEPOSIT_USD = 1000.00

    def __init__(self, database):
        self.db = database
        self.wallets_table = self.db.db.table('wallets')
        self.transactions_table = self.db.db.table('transactions')
        self.deposits_table = self.db.db.table('deposits')

        # Initialize wallet system
        logger.info("🏦 Wallet system initialized")

    def get_user_balance(self, user_id: int) -> float:
        """Get user's current wallet balance"""
        User = Query()
        wallet = self.wallets_table.search(User.user_id == user_id)

        if not wallet:
            # Create new wallet for user
            self._create_wallet(user_id)
            return 0.00

        return float(wallet[0].get('balance', 0.00))

    def _create_wallet(self, user_id: int) -> None:
        """Create a new wallet for user"""
        wallet_data = {
            'user_id': user_id,
            'balance': 0.00,
            'total_deposited': 0.00,
            'total_spent': 0.00,
            'total_refunded': 0.00,
            'created_at': datetime.now().isoformat(),
            'last_activity': datetime.now().isoformat()
        }

        self.wallets_table.insert(wallet_data)
        logger.info("🏦 New wallet created for user %s", user_id)

    def has_sufficient_balance(self, user_id: int, amount: float) -> bool:
        """Check if user has sufficient balance for a transaction"""
        current_balance = self.get_user_balance(user_id)
        return current_balance >= amount

    def deduct_balance(self, user_id: int, amount: float, description: str, order_id: Optional[str] = None) -> bool:
        """
        Deduct amount from user's wallet balance
        Returns True if successful, False if insufficient funds
        """
        try:
            current_balance = self.get_user_balance(user_id)

            if current_balance < amount:
                logger.warning(
                    "💰 Insufficient balance for user %s: $%.2f < $%.2f", user_id, current_balance, amount)
                return False

            new_balance = current_balance - amount

            # Update wallet
            User = Query()
            self.wallets_table.update({
                'balance': round(new_balance, 2),
                'total_spent': self.wallets_table.search(User.user_id == user_id)[0].get('total_spent', 0) + amount,
                'last_activity': datetime.now().isoformat()
            }, User.user_id == user_id)

            # Record transaction
            self._record_transaction(
                user_id=user_id,
                transaction_type='deduction',
                amount=amount,
                description=description,
                order_id=order_id,
                balance_after=new_balance
            )

            logger.info(
                "💰 Deducted $%.2f from user %s wallet. New balance: $%.2f", amount, user_id, new_balance)
            return True

        except (ValueError, TypeError, RuntimeError) as e:
            logger.error(
                "❌ Error deducting balance for user %s: %s", user_id, str(e))
            return False

    def add_balance(self, user_id: int, amount: float, description: str, transaction_type: str = 'deposit') -> bool:
        """
        Add amount to user's wallet balance
        transaction_type can be 'deposit', 'refund', 'admin_credit'
        """
        try:
            current_balance = self.get_user_balance(user_id)
            new_balance = current_balance + amount

            # Update wallet
            User = Query()
            wallet_data = self.wallets_table.search(User.user_id == user_id)[0]

            update_data = {
                'balance': round(new_balance, 2),
                'last_activity': datetime.now().isoformat()
            }

            if transaction_type == 'deposit':
                update_data['total_deposited'] = wallet_data.get(
                    'total_deposited', 0) + amount
            elif transaction_type == 'refund':
                update_data['total_refunded'] = wallet_data.get(
                    'total_refunded', 0) + amount

            self.wallets_table.update(update_data, User.user_id == user_id)

            # Record transaction
            self._record_transaction(
                user_id=user_id,
                transaction_type=transaction_type,
                amount=amount,
                description=description,
                balance_after=new_balance
            )

            logger.info(
                "💰 Added $%.2f to user %s wallet. New balance: $%.2f", amount, user_id, new_balance)
            return True

        except (ValueError, TypeError, RuntimeError) as e:
            logger.error(
                "❌ Error adding balance for user %s: %s", user_id, str(e))
            return False

    def _record_transaction(self, user_id: int, transaction_type: str, amount: float,
                            description: str, order_id: Optional[str] = None,
                            balance_after: Optional[float] = None) -> None:
        """Record a transaction in the transaction history"""
        transaction = {
            'user_id': user_id,
            # deduction, deposit, refund, admin_credit
            'transaction_type': transaction_type,
            'amount': round(amount, 2),
            'description': description,
            'order_id': order_id,
            'balance_after': round(balance_after or self.get_user_balance(user_id), 2),
            'timestamp': datetime.now().isoformat(),
            'transaction_id': f"TXN_{user_id}_{int(datetime.now().timestamp())}"
        }

        self.transactions_table.insert(transaction)

    def get_transaction_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get user's transaction history"""
        User = Query()
        transactions = self.transactions_table.search(User.user_id == user_id)

        # Sort by timestamp (newest first) and limit
        sorted_transactions = sorted(
            transactions,
            key=lambda x: x['timestamp'],
            reverse=True
        )[:limit]

        return sorted_transactions

    def create_deposit_request(self, user_id: int, amount: float, binance_wallet: str) -> Dict[str, Any]:
        """
        Create a deposit request that requires admin approval
        """
        if amount < self.MIN_DEPOSIT_USD:
            raise ValueError(f"Minimum deposit is ${self.MIN_DEPOSIT_USD}")

        if amount > self.MAX_DEPOSIT_USD:
            raise ValueError(f"Maximum deposit is ${self.MAX_DEPOSIT_USD}")

        deposit_id = f"DEP_{user_id}_{int(datetime.now().timestamp())}"

        deposit_data = {
            'deposit_id': deposit_id,
            'user_id': user_id,
            'amount_usd': round(amount, 2),
            'binance_wallet': binance_wallet,
            'status': 'pending_payment',
            'created_at': datetime.now().isoformat(),
            # 2 hours to pay
            'expires_at': (datetime.now() + timedelta(hours=2)).isoformat(),
            'paid_at': None,
            'admin_approved_at': None,
            'admin_approved_by': None
        }

        self.deposits_table.insert(deposit_data)

        # Generate deposit instructions
        instructions = {
            'deposit_id': deposit_id,
            'amount_usd': amount,
            'binance_wallet': binance_wallet,
            'instructions': [
                f"💰 **Wallet Deposit: ${amount:.2f}**",
                f"🏦 **Binance Wallet:** `{binance_wallet}`",
                "",
                "📋 **Deposit Instructions:**",
                f"1. Send exactly ${amount:.2f} USDT to the wallet above",
                "2. Take a screenshot of the transaction",
                "3. Click 'Payment Sent' below",
                "4. Admin will verify and approve your deposit",
                "",
                f"🆔 **Deposit ID:** `{deposit_id}`",
                "⏰ **Deposit expires in 2 hours**",
                "",
                f"✅ Minimum deposit: ${self.MIN_DEPOSIT_USD}",
                "💡 Your wallet balance will be updated automatically after approval!"
            ]
        }

        logger.info(
            "🏦 Deposit request created for user %s: %s ($%.2f)", user_id, deposit_id, amount)
        return instructions

    def create_binance_deposit_request(self, user_id: int, amount: float, binance_id: str) -> Dict[str, Any]:
        """
        Create a Binance deposit request that requires admin approval
        """
        if amount < self.MIN_DEPOSIT_USD:
            raise ValueError(f"Minimum deposit is ${self.MIN_DEPOSIT_USD}")

        if amount > self.MAX_DEPOSIT_USD:
            raise ValueError(f"Maximum deposit is ${self.MAX_DEPOSIT_USD}")

        deposit_id = f"BIN_{user_id}_{int(datetime.now().timestamp())}"

        deposit_data = {
            'deposit_id': deposit_id,
            'user_id': user_id,
            'amount_usd': round(amount, 2),
            'deposit_method': 'binance',
            'binance_id': binance_id,
            'status': 'pending_payment',
            'created_at': datetime.now().isoformat(),
            # 2 hours to pay
            'expires_at': (datetime.now() + timedelta(hours=2)).isoformat(),
            'paid_at': None,
            'admin_approved_at': None,
            'admin_approved_by': None
        }

        self.deposits_table.insert(deposit_data)

        logger.info(
            "🟡 Binance deposit request created for user %s: %s ($%.2f)", user_id, deposit_id, amount)

        return {
            'deposit_id': deposit_id,
            'amount_usd': amount,
            'binance_id': binance_id
        }

    def approve_deposit(self, deposit_id: str, admin_id: int) -> bool:
        """Approve a deposit request and add funds to user wallet"""
        try:
            Deposit = Query()
            deposit_record = self.deposits_table.search(
                Deposit.deposit_id == deposit_id)

            if not deposit_record:
                logger.error("Deposit %s not found", deposit_id)
                return False

            deposit = deposit_record[0]

            # Check if deposit is still valid
            expires_at = datetime.fromisoformat(deposit['expires_at'])
            if datetime.now() > expires_at:
                logger.error("Deposit %s has expired", deposit_id)
                return False

            if deposit['status'] != 'pending_payment':
                logger.error("Deposit %s already processed", deposit_id)
                return False

            # Update deposit status
            self.deposits_table.update({
                'status': 'approved',
                'paid_at': datetime.now().isoformat(),
                'admin_approved_at': datetime.now().isoformat(),
                'admin_approved_by': str(admin_id)
            }, Deposit.deposit_id == deposit_id)

            # Add funds to user wallet
            success = self.add_balance(
                user_id=deposit['user_id'],
                amount=deposit['amount_usd'],
                description=f"Deposit approved by admin (ID: {deposit_id})",
                transaction_type='deposit'
            )

            if success:
                logger.info(
                    "✅ Deposit %s approved by admin %s", deposit_id, admin_id)
                return True
            else:
                logger.error(
                    "❌ Failed to add balance for deposit %s", deposit_id)
                return False

        except (ValueError, TypeError, RuntimeError) as e:
            logger.error("❌ Error approving deposit %s: %s",
                         deposit_id, str(e))
            return False

    def get_pending_deposits(self) -> List[Dict]:
        """Get all pending deposit requests"""
        Deposit = Query()
        pending = self.deposits_table.search(
            Deposit.status == 'pending_payment')

        # Filter out expired deposits
        valid_deposits = []
        for deposit in pending:
            expires_at = datetime.fromisoformat(deposit['expires_at'])
            if datetime.now() <= expires_at:
                valid_deposits.append(deposit)

        return valid_deposits

    def get_deposit_status(self, deposit_id: str) -> Optional[Dict]:
        """Get deposit request status"""
        Deposit = Query()
        deposits = self.deposits_table.search(Deposit.deposit_id == deposit_id)
        return deposits[0] if deposits else None

    def get_wallet_summary(self, user_id: int) -> Dict[str, Any]:
        """Get comprehensive wallet summary for user"""
        balance = self.get_user_balance(user_id)
        transactions = self.get_transaction_history(user_id, limit=5)

        User = Query()
        wallet_data = self.wallets_table.search(User.user_id == user_id)
        wallet_info = wallet_data[0] if wallet_data else {}

        return {
            'balance': balance,
            'total_deposited': wallet_info.get('total_deposited', 0.00),
            'total_spent': wallet_info.get('total_spent', 0.00),
            'total_refunded': wallet_info.get('total_refunded', 0.00),
            'recent_transactions': transactions,
            'wallet_created': wallet_info.get('created_at'),
            'last_activity': wallet_info.get('last_activity')
        }

    def reserve_balance(self, user_id: int, amount: float, order_id: str, description: str) -> bool:
        """
        Reserve amount from user's wallet balance without actually deducting it
        Returns True if successful, False if insufficient funds
        """
        try:
            current_balance = self.get_user_balance(user_id)

            if current_balance < amount:
                logger.warning(
                    "💰 Insufficient balance for reservation - user %s: $%.2f < $%.2f", user_id, current_balance, amount)
                return False

            # Record reservation transaction (but don't actually deduct yet)
            self._record_transaction(
                user_id=user_id,
                transaction_type='reservation',
                amount=amount,
                description=f"Reserved for {description}",
                order_id=order_id,
                balance_after=current_balance  # Balance unchanged during reservation
            )

            logger.info(
                "🔒 Reserved $%.2f for user %s (order: %s). Balance remains: $%.2f", amount, user_id, order_id, current_balance)
            return True

        except (ValueError, TypeError, RuntimeError) as e:
            logger.error(
                "❌ Error reserving balance for user %s: %s", user_id, str(e))
            return False

    def confirm_reservation(self, user_id: int, amount: float, order_id: str, description: str) -> bool:
        """
        Confirm a reservation by actually deducting the amount from wallet balance
        Should only be called when OTP is successfully received
        """
        try:
            current_balance = self.get_user_balance(user_id)

            if current_balance < amount:
                logger.error(
                    "💰 CRITICAL: Insufficient balance for confirmation - user %s: $%.2f < $%.2f", user_id, current_balance, amount)
                return False

            new_balance = current_balance - amount

            # Update wallet
            User = Query()
            self.wallets_table.update({
                'balance': round(new_balance, 2),
                'total_spent': self.wallets_table.search(User.user_id == user_id)[0].get('total_spent', 0) + amount,
                'last_activity': datetime.now().isoformat()
            }, User.user_id == user_id)

            # Record final deduction transaction
            self._record_transaction(
                user_id=user_id,
                transaction_type='deduction',
                amount=amount,
                description=f"Confirmed: {description}",
                order_id=order_id,
                balance_after=new_balance
            )

            logger.info(
                "✅ Confirmed reservation $%.2f for user %s (order: %s). New balance: $%.2f", amount, user_id, order_id, new_balance)
            return True

        except (ValueError, TypeError, RuntimeError) as e:
            logger.error(
                "❌ Error confirming reservation for user %s: %s", user_id, str(e))
            return False

    def cancel_reservation(self, user_id: int, amount: float, order_id: str, reason: str = "Order cancelled") -> bool:
        """
        Cancel a reservation (no actual refund needed since money was never deducted)
        Just record the cancellation for audit trail
        """
        try:
            current_balance = self.get_user_balance(user_id)

            # Record cancellation transaction
            self._record_transaction(
                user_id=user_id,
                transaction_type='cancellation',
                amount=amount,
                description=f"Cancelled reservation: {reason}",
                order_id=order_id,
                balance_after=current_balance  # Balance unchanged
            )

            logger.info(
                "🚫 Cancelled reservation $%.2f for user %s (order: %s). Balance remains: $%.2f", amount, user_id, order_id, current_balance)
            return True

        except (ValueError, TypeError, RuntimeError) as e:
            logger.error(
                "❌ Error cancelling reservation for user %s: %s", user_id, str(e))
            return False

    def process_service_purchase(self, user_id: int, service_price: float, service_name: str, order_id: str) -> bool:
        """
        DEPRECATED: Use reserve_balance() instead followed by confirm_reservation() when OTP received
        Process a service purchase by deducting from wallet balance
        Returns True if successful, False if insufficient funds
        """
        logger.warning(
            "⚠️ DEPRECATED: process_service_purchase() called. Use reserve_balance() + confirm_reservation() instead")
        return self.deduct_balance(
            user_id=user_id,
            amount=service_price,
            description=f"{service_name} service purchase",
            order_id=order_id
        )

    def process_refund(self, user_id: int, refund_amount: float, order_id: str, reason: str = "Order refund") -> bool:
        """
        Process a refund by adding amount back to wallet balance
        INCLUDES DUPLICATE REFUND PROTECTION
        """
        # CRITICAL SECURITY CHECK: Prevent duplicate refunds for same order
        Transaction = Query()
        existing_refund = self.transactions_table.search(
            (Transaction.user_id == user_id) &
            (Transaction.transaction_type == 'refund') &
            (Transaction.description.matches(f'.*order {order_id}.*'))
        )

        if existing_refund:
            logger.warning(
                "🚨 DUPLICATE REFUND BLOCKED: Order %s already refunded for user %s",
                order_id, user_id
            )
            return False

        return self.add_balance(
            user_id=user_id,
            amount=refund_amount,
            description=f"Refund for order {order_id}: {reason}",
            transaction_type='refund'
        )

    def get_all_wallets_summary(self) -> Dict[str, Any]:
        """Get summary of all wallets for admin dashboard"""
        all_wallets = self.wallets_table.all()

        total_balance = sum(w.get('balance', 0) for w in all_wallets)
        total_deposited = sum(w.get('total_deposited', 0) for w in all_wallets)
        total_spent = sum(w.get('total_spent', 0) for w in all_wallets)
        total_refunded = sum(w.get('total_refunded', 0) for w in all_wallets)

        return {
            'total_users': len(all_wallets),
            'total_balance': round(total_balance, 2),
            'total_deposited': round(total_deposited, 2),
            'total_spent': round(total_spent, 2),
            'total_refunded': round(total_refunded, 2),
            'pending_deposits': len(self.get_pending_deposits())
        }
