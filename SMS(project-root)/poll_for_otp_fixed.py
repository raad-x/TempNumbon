async def poll_for_otp(order_id: Union[int, str], user_id: int, context: ContextTypes.DEFAULT_TYPE):
    """Optimized high-frequency OTP polling with intelligent intervals"""
    start_time = datetime.now()
    poll_count = 0
    consecutive_failures = 0
    last_status = None

    try:
        user_logger.info(
            "🔄 Starting optimized OTP polling for order %s (user: %s)", order_id, user_id)
        performance_logger.info(
            "⏱️ OTP polling initiated with adaptive intervals")

        if not sms_api:
            logger.error("❌ SMS API not initialized for polling")
            return

        while (datetime.now() - start_time).total_seconds() < POLL_TIMEOUT:
            poll_count += 1
            poll_start = asyncio.get_event_loop().time()

            # Dynamic polling interval based on time elapsed
            elapsed = (datetime.now() - start_time).total_seconds()
            if elapsed < 60:  # First minute: every 2 seconds
                interval = 2
            elif elapsed < 180:  # Next 2 minutes: every 3 seconds
                interval = 3
            elif elapsed < 300:  # Next 2 minutes: every 5 seconds
                interval = 5
            else:  # After 5 minutes: every 10 seconds
                interval = 10

            api_logger.debug(
                "🔍 Poll #%s for order %s (interval: %ss)", poll_count, order_id, interval)

            try:
                # Check OTP status with timeout
                result = await asyncio.wait_for(
                    sms_api.get_order_status(str(order_id)),
                    timeout=10.0  # 10 second timeout per API call
                )

                poll_duration = asyncio.get_event_loop().time() - poll_start
                performance_logger.debug(
                    "⚡ API status check completed in %.2fs", poll_duration)

                consecutive_failures = 0  # Reset failure counter on success

                if result.get('success'):
                    status = result.get('status', '')

                    # Log status changes for debugging
                    if status != last_status:
                        api_logger.info(
                            "📊 Order %s status changed: %s → %s", order_id, last_status, status)
                        last_status = status

                        # Special logging for processing status (previously thought to be cancelled)
                        if status == 'processing':
                            api_logger.info(
                                "🔄 Order %s is now processing - SMS dispatched, waiting for delivery", order_id)
                        elif status.startswith('unknown_'):
                            api_logger.warning(
                                "⚠️ Order %s has unknown status: %s - continuing to poll", order_id, status)

                    # DEBUG: Log full API response for processing and success status
                    if status in ['processing', 'success']:
                        api_logger.info(
                            "🔍 Order %s API response: status=%s, sms=%s, full_response=%s",
                            order_id, status, result.get('sms'), result)

                    # SUCCESS: OTP received! (Check both 'success' and 'processing' status)
                    # SMSPool API may return SMS content with status 3 (processing)
                    if status in ['success', 'processing'] and (result.get('sms') or result.get('otp')):
                        otp_text = result.get(
                            'sms', '') or result.get('otp', '')

                        # Enhanced OTP extraction with multiple patterns
                        otp_patterns = [
                            r'\b(\d{6})\b',  # 6-digit codes (most common)
                            r'\b(\d{4})\b',  # 4-digit codes
                            r'\b(\d{5})\b',  # 5-digit codes
                            r'\b(\d{7,8})\b',  # 7-8 digit codes
                            # Pattern with keywords
                            r'(?:code|verification|pin):\s*(\d+)',
                            r'(\d+)',  # Any sequence of digits as fallback
                        ]

                        otp_code = None
                        for pattern in otp_patterns:
                            match = re.search(pattern, otp_text, re.IGNORECASE)
                            if match:
                                otp_code = match.group(1)
                                break

                        otp_code = otp_code or otp_text  # Fallback to full text

                        # Update database with detailed info
                        try:
                            # Update order status with OTP completion
                            db.update_order_status(
                                order_id, 'completed', otp_code)
                            user_logger.info(
                                "✅ Order %s completed - OTP: %s", order_id, otp_code)
                        except (OSError, RuntimeError, ValueError) as db_err:
                            logger.error(
                                "❌ Database update failed: %s", db_err)

                        # Send optimized success message to user
                        # Create buttons for after OTP is received
                        success_keyboard = [
                            [
                                InlineKeyboardButton(
                                    "📱 Buy Another", callback_data="browse_services"),
                                InlineKeyboardButton(
                                    "💰 Check Balance", callback_data="show_balance")
                            ],
                            [
                                InlineKeyboardButton(
                                    "🆔 Order History", callback_data="transaction_history"),
                                InlineKeyboardButton(
                                    "🏠 Main Menu", callback_data="back_to_start")
                            ]
                        ]
                        success_reply_markup = InlineKeyboardMarkup(
                            success_keyboard)

                        total_time = (datetime.now() -
                                      start_time).total_seconds()
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=f"🎉 <b>OTP Code Received!</b>\n\n"
                            f"👉 <b>Your Code:</b> <code>{otp_code}</code>\n\n"
                            f"📱 <b>Full SMS:</b> {otp_text}\n\n"
                            f"🆔 <b>Order:</b> #{order_id}\n"
                            f"⚡ <b>Delivery Time:</b> {total_time:.1f} seconds\n"
                            f"🔄 <b>Polls Required:</b> {poll_count}\n\n"
                            f"✨ <b>Ready to use immediately!</b>",
                            parse_mode='HTML',
                            reply_markup=success_reply_markup
                        )

                        performance_logger.info(
                            "🎯 OTP delivered for order %s in %.1fs after %s polls", order_id, total_time, poll_count)
                        break

                    # Handle terminal status states (should stop polling)
                    elif status in ['cancelled', 'expired', 'timeout']:
                        api_logger.warning(
                            "🛑 Order %s reached terminal status: %s - stopping polling", order_id, status)

                        # Update database status
                        try:
                            db.update_order_status(order_id, status)
                        except (OSError, RuntimeError, ValueError) as db_err:
                            logger.error(
                                "❌ Database status update failed: %s", db_err)

                        # Notify user about terminal status
                        terminal_keyboard = [
                            [
                                InlineKeyboardButton(
                                    "💰 Request Refund", callback_data=f"refund_{order_id}"),
                                InlineKeyboardButton(
                                    "📱 Try Again", callback_data="browse_services")
                            ],
                            [
                                InlineKeyboardButton(
                                    "💳 Check Balance", callback_data="show_balance"),
                                InlineKeyboardButton(
                                    "🏠 Main Menu", callback_data="back_to_start")
                            ]
                        ]
                        terminal_reply_markup = InlineKeyboardMarkup(
                            terminal_keyboard)

                        status_messages = {
                            'cancelled': '🚫 <b>Order Cancelled</b>\n\nThis order was cancelled by the provider.',
                            'expired': '⏰ <b>Order Expired</b>\n\nThis order has expired and is no longer active.',
                            'timeout': '🕒 <b>Order Timeout</b>\n\nThis order timed out waiting for SMS delivery.'
                        }

                        total_time = (datetime.now() -
                                      start_time).total_seconds()
                        await context.bot.send_message(
                            chat_id=user_id,
                            text=f"{status_messages.get(status, '❌ Order Failed')}\n\n"
                            f"🆔 <b>Order:</b> #{order_id}\n"
                            f"⏱️ <b>Duration:</b> {total_time:.1f} seconds\n"
                            f"🔄 <b>Total Polls:</b> {poll_count}\n\n"
                            f"💰 <b>Refund available</b> - Use button below to request refund.",
                            parse_mode='HTML',
                            reply_markup=terminal_reply_markup
                        )
                        break

                    # Continue polling for pending/processing statuses
                    # (no action needed - loop will continue)

            except asyncio.TimeoutError:
                consecutive_failures += 1
                api_logger.warning(
                    "⏰ Timeout during poll #%s for order %s (attempt %s)",
                    poll_count, order_id, consecutive_failures)

                # Stop if too many consecutive timeouts
                if consecutive_failures >= 3:
                    api_logger.error(
                        "❌ Too many consecutive timeouts for order %s - stopping polling", order_id)
                    break

            except Exception as api_error:
                consecutive_failures += 1
                api_logger.error(
                    "❌ API error during poll #%s for order %s: %s", poll_count, order_id, str(api_error))

                # Stop if too many consecutive failures
                if consecutive_failures >= 5:
                    api_logger.error(
                        "❌ Too many consecutive failures for order %s - stopping polling", order_id)
                    break

            # Adaptive sleep based on current interval
            await asyncio.sleep(interval)

        else:
            # TIMEOUT: No OTP received within time limit
            try:
                db.update_order_status(order_id, 'timeout')
            except (OSError, RuntimeError, ValueError) as db_err:
                logger.error("❌ Database timeout update failed: %s", db_err)

            # Create refund buttons for timeout scenario
            timeout_keyboard = [
                [
                    InlineKeyboardButton(
                        "💰 Request Refund", callback_data=f"refund_{order_id}"),
                    InlineKeyboardButton(
                        "📱 Try Again", callback_data="browse_services")
                ],
                [
                    InlineKeyboardButton(
                        "💳 Check Balance", callback_data="show_balance"),
                    InlineKeyboardButton(
                        "🏠 Main Menu", callback_data="back_to_start")
                ]
            ]
            timeout_reply_markup = InlineKeyboardMarkup(timeout_keyboard)

            total_time = (datetime.now() - start_time).total_seconds()
            await context.bot.send_message(
                chat_id=user_id,
                text=f"⏰ <b>SMS Delivery Timeout</b>\n\n"
                f"🆔 <b>Order:</b> #{order_id}\n"
                f"⏱️ <b>Duration:</b> {POLL_TIMEOUT//60} minutes\n"
                f"🔄 <b>Total Polls:</b> {poll_count}\n\n"
                f"💰 <b>Automatic refund will be processed</b>\n"
                f"Contact support if you need assistance.",
                parse_mode='HTML',
                reply_markup=timeout_reply_markup
            )

            performance_logger.warning(
                "⏰ Order %s timed out after %s polls in %.1fs", order_id, poll_count, total_time)

    except asyncio.CancelledError:
        user_logger.info(
            "🛑 OTP polling cancelled for order %s after %s polls", order_id, poll_count)
        raise
    except Exception as e:
        logger.error(
            "❌ Critical error in OTP polling for order %s: %s", order_id, str(e))

        # Safely update database status if possible
        try:
            db.update_order_status(order_id, 'error')
        except Exception as db_error:
            logger.error(
                "❌ Failed to update order status during error handling: %s", db_error)

        # Send error notification to user
        try:
            error_keyboard = [
                [
                    InlineKeyboardButton(
                        "💰 Request Refund", callback_data=f"refund_{order_id}"),
                    InlineKeyboardButton(
                        "📱 Try Again", callback_data="browse_services")
                ],
                [
                    InlineKeyboardButton(
                        "💳 Check Balance", callback_data="show_balance"),
                    InlineKeyboardButton(
                        "🏠 Main Menu", callback_data="back_to_start")
                ]
            ]
            error_reply_markup = InlineKeyboardMarkup(error_keyboard)

            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ <b>Service Error</b>\n\n"
                f"🆔 <b>Order:</b> #{order_id}\n"
                f"🔄 <b>Polls:</b> {poll_count}\n\n"
                f"A technical error occurred. Please request a refund or try again.",
                parse_mode='HTML',
                reply_markup=error_reply_markup
            )
        except Exception as notification_error:
            logger.error(
                "❌ Failed to send error notification: %s", notification_error)

    finally:
        performance_logger.info(
            "🧹 Polling cleanup completed for order %s", order_id)

        # Remove from active polls tracking
        if order_id in active_polls:
            active_polls.pop(order_id, None)
