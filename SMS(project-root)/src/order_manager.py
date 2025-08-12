"""
Order management system for Ring4 SMS Bot
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import re

logger = logging.getLogger(__name__)


class OrderManager:
    """Manages Ring4 orders and OTP polling"""

    def __init__(self, database, smspool_api):
        self.db = database
        self.api = smspool_api
        self.active_polls: Dict[int, asyncio.Task] = {}

    def create_order(self, user_id: int, payment_id: str, order_data: Dict) -> int:
        """Create a new order record after payment approval"""
        order = {
            'user_id': user_id,
            'payment_id': payment_id,
            'order_id': order_data.get('order_id'),
            'number': order_data.get('number'),
            'cost': order_data.get('cost'),
            'service': order_data.get('service', 'Ring4'),
            'country': order_data.get('country', 'US'),
            'status': 'active',  # Order is active, waiting for OTP
            'created_at': datetime.now().isoformat(),
            # 10 minutes
            'expires_at': (datetime.now() + timedelta(seconds=600)).isoformat(),
            'otp': None,
            'otp_received_at': None,
            'poll_count': 0
        }

        doc_id = self.db.orders.insert(order)
        logger.info(
            f"📝 Order created: {order['order_id']} for user {user_id} (Payment: {payment_id})")
        return doc_id

    def update_order_status(self, order_id: int, status: str, otp: Optional[str] = None):
        """Update order status and OTP if provided"""
        from tinydb import Query
        Order = Query()
        update_data = {'status': status}

        if otp:
            update_data['otp'] = otp
            update_data['otp_received_at'] = datetime.now().isoformat()

        self.db.orders.update(update_data, Order.order_id == order_id)
        logger.info(f"🔄 Order {order_id} status updated to: {status}")

    def get_order(self, order_id: int) -> Optional[Dict]:
        """Get order by ID"""
        from tinydb import Query
        Order = Query()
        result = self.db.orders.search(Order.order_id == order_id)
        return result[0] if result else None

    def get_user_orders(self, user_id: int, status: Optional[str] = None) -> List[Dict]:
        """Get orders for a user, optionally filtered by status"""
        from tinydb import Query
        Order = Query()
        if status:
            return [dict(doc) for doc in self.db.orders.search((Order.user_id == user_id) & (Order.status == status))]
        return [dict(doc) for doc in self.db.orders.search(Order.user_id == user_id)]

    async def start_otp_polling(self, order_id: int, user_id: int, context) -> asyncio.Task:
        """Start high-frequency OTP polling (5 second intervals for 10 minutes)"""
        if order_id in self.active_polls:
            self.active_polls[order_id].cancel()

        task = asyncio.create_task(
            self._poll_for_otp(order_id, user_id, context))
        self.active_polls[order_id] = task
        logger.info(f"🔄 Started OTP polling for order {order_id}")
        return task

    async def _poll_for_otp(self, order_id: int, user_id: int, context):
        """Internal OTP polling with 5-second intervals and 10-minute timeout"""
        start_time = datetime.now()
        poll_count = 0
        POLL_INTERVAL = 5  # 5 seconds (high frequency for speed)
        POLL_TIMEOUT = 600  # 10 minutes total

        try:
            logger.info(
                f"🔄 Starting high-frequency OTP polling for order {order_id} (5s intervals, 10min timeout)")

            while (datetime.now() - start_time).total_seconds() < POLL_TIMEOUT:
                poll_count += 1

                # Update poll count in database
                from tinydb import Query
                Order = Query()
                self.db.orders.update(
                    {'poll_count': poll_count}, Order.order_id == order_id)

                # Check OTP status
                result = await self.api.check_otp_status(order_id)

                if result.get('success') and result.get('otp_found'):
                    # OTP received!
                    otp_text = result.get('sms', '')

                    # Extract OTP from SMS text (look for 4-8 digit numbers)
                    otp_match = re.search(r'\b\d{4,8}\b', otp_text)
                    otp_code = otp_match.group() if otp_match else otp_text

                    # Update order status
                    self.update_order_status(order_id, 'completed', otp_code)

                    # Send OTP to user immediately
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=f"✅ <b>Ring4 OTP Received!</b>\n\n"
                        f"📱 <b>Your Code:</b> <code>{otp_code}</code>\n\n"
                        f"📄 <b>Full SMS:</b> {otp_text}\n\n"
                        f"🆔 <b>Order:</b> #{order_id}\n"
                        f"⏱️ <b>Delivered after:</b> {poll_count} checks ({(datetime.now() - start_time).total_seconds():.1f}s)\n\n"
                        f"🎯 Use this code for your Ring4 verification!",
                        parse_mode='HTML'
                    )

                    logger.info(
                        f"✅ OTP delivered for order {order_id}: {otp_code} (after {poll_count} polls)")
                    break

                # Log polling progress every 12 polls (1 minute)
                if poll_count % 12 == 0:
                    minutes_elapsed = (
                        datetime.now() - start_time).total_seconds() / 60
                    logger.info(
                        f"🔄 Order {order_id}: {poll_count} polls completed ({minutes_elapsed:.1f}min elapsed)")

                # Wait before next poll
                await asyncio.sleep(POLL_INTERVAL)

            else:
                # Timeout reached - no OTP received
                self.update_order_status(order_id, 'timeout')

                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"⏰ <b>Order Timeout</b>\n\n"
                    f"❌ No OTP received within 10 minutes\n"
                    f"📱 <b>Order:</b> #{order_id}\n"
                    f"🔍 <b>Total checks:</b> {poll_count}\n\n"
                    f"💰 <b>Refund Available:</b> Use /refund to request refund\n"
                    f"👨‍💼 Admin will review and process your refund request",
                    parse_mode='HTML'
                )

                logger.warning(
                    f"⏰ Order {order_id} timed out after {poll_count} polls (10 minutes)")

        except asyncio.CancelledError:
            logger.info(f"🛑 OTP polling cancelled for order {order_id}")
            raise
        except Exception as e:
            logger.error(f"❌ Error polling for order {order_id}: {str(e)}")
            self.update_order_status(order_id, 'error')

            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"❌ <b>Polling Error</b>\n\n"
                    f"Error checking for OTP: {str(e)}\n"
                    f"📱 <b>Order:</b> #{order_id}\n\n"
                    f"💰 <b>Refund Available:</b> Use /refund to request refund",
                    parse_mode='HTML'
                )
            except:
                pass

        finally:
            # Clean up polling task
            if order_id in self.active_polls:
                del self.active_polls[order_id]
                logger.info(f"🧹 Cleaned up polling task for order {order_id}")

    def stop_polling(self, order_id: int):
        """Stop OTP polling for an order"""
        if order_id in self.active_polls:
            self.active_polls[order_id].cancel()
            del self.active_polls[order_id]
            logger.info(f"🛑 Stopped polling for order {order_id}")

    def get_active_polls(self) -> List[int]:
        """Get list of orders currently being polled"""
        return list(self.active_polls.keys())

    def format_order_info(self, order: Dict) -> str:
        """Format order information for display"""
        created = datetime.fromisoformat(
            order['created_at']).strftime('%Y-%m-%d %H:%M')
        status_emoji = {
            'active': '🟡',
            'completed': '✅',
            'timeout': '⏰',
            'refunded': '💰',
            'error': '❌'
        }

        info = (
            f"{status_emoji.get(order['status'], '❓')} <b>Order #{order['order_id']}</b>\n"
            f"📱 <b>Number:</b> <code>{order['number']}</code>\n"
            f"💰 <b>Cost:</b> ${order['cost']}\n"
            f"🌎 <b>Service:</b> {order['service']} ({order['country']})\n"
            f"📅 <b>Created:</b> {created}\n"
            f"🔄 <b>Status:</b> {order['status'].title()}"
        )

        if order.get('poll_count', 0) > 0:
            info += f"\n🔍 <b>Checks:</b> {order['poll_count']}"

        if order.get('otp'):
            info += f"\n📱 <b>OTP:</b> <code>{order['otp']}</code>"

        return info
