import aiohttp
import logging
import re
import json
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class SMSPoolAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.smspool.net"

    async def check_balance(self) -> Dict[str, Any]:
        """Check account balance with enhanced error handling"""
        if not self.api_key or self.api_key.strip() == "":
            return {
                'success': False,
                'balance': '0',
                'message': 'API key not configured'
            }

        url = f"{self.base_url}/request/balance"
        params = {'key': self.api_key}

        try:
            timeout = aiohttp.ClientTimeout(total=15)
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                            balance = data.get('balance', '0')
                            # Validate balance is numeric
                            try:
                                float(balance)
                            except (ValueError, TypeError):
                                balance = '0'
                            return {
                                'success': True,
                                'balance': balance,
                                'message': f"Current balance: ${balance}"
                            }
                        except Exception as json_error:
                            logger.error(
                                f"❌ Failed to parse balance response JSON: {json_error}")
                            text_response = await response.text()
                            logger.debug(
                                f"Raw response: {text_response[:200]}...")
                            return {
                                'success': False,
                                'balance': '0',
                                'message': 'Invalid response format from balance API'
                            }
                    elif response.status == 401:
                        return {
                            'success': False,
                            'balance': '0',
                            'message': 'Invalid API key - please check your configuration'
                        }
                    elif response.status == 429:
                        return {
                            'success': False,
                            'balance': '0',
                            'message': 'Rate limit exceeded - please try again later'
                        }
                    else:
                        try:
                            error_data = await response.json()
                            error_msg = error_data.get(
                                'message', f'HTTP {response.status} error')
                        except:
                            error_msg = f'Balance check failed (HTTP {response.status})'
                        return {
                            'success': False,
                            'balance': '0',
                            'message': error_msg
                        }
        except aiohttp.ClientConnectorError as conn_error:
            logger.error(
                f"❌ Connection error during balance check: {conn_error}")
            return {
                'success': False,
                'balance': '0',
                'message': 'Unable to connect to SMSPool API - please check your internet connection'
            }
        except aiohttp.ServerTimeoutError:
            logger.error("❌ Timeout during balance check")
            return {
                'success': False,
                'balance': '0',
                'message': 'Request timeout - SMSPool API is responding slowly'
            }
        except Exception as e:
            logger.error(f"❌ Unexpected error during balance check: {str(e)}")
            return {
                'success': False,
                'balance': '0',
                'message': f'Network error: {str(e)}'
            }

    async def purchase_ring4_number(self, service_id: int = 1574, country_id: int = 1) -> Dict[str, Any]:
        """Purchase a Ring4 US number with smart service fallback and pricing transparency"""
        logger.info("🎯 Starting Ring4 purchase with smart fallback...")

        # Define alternative services with expected pricing
        alternative_services = [
            {'id': 1574, 'name': 'Ring4', 'expected_price': 0.17},
            {'id': 22, 'name': 'Telegram', 'expected_price': 0.25},
            {'id': 395, 'name': 'Google', 'expected_price': 0.42},
            {'id': 1012, 'name': 'WhatsApp', 'expected_price': 0.35},
        ]

        # Try each service in order
        for service in alternative_services:
            service_id = service['id']
            service_name = service['name']
            expected_price = service['expected_price']

            logger.info(
                f"🔄 Attempting {service_name} (ID: {service_id}, expected: ${expected_price})")

            try:
                result = await self._purchase_sms_service(service_id, service_name)
                if result.get('success'):
                    # Calculate price warning
                    actual_cost = float(result.get('cost', expected_price))

                    if service_name == 'Ring4':
                        # Ring4 worked, no warning needed
                        result['price_warning'] = None
                        logger.info(
                            f"✅ Ring4 purchase successful at ${actual_cost}")
                    else:
                        # Alternative service used
                        price_difference = round(
                            actual_cost - 0.17, 2)  # vs Ring4 expected
                        result['price_warning'] = {
                            'service_used': service_name,
                            'actual_cost': actual_cost,
                            'ring4_expected': 0.17,
                            'price_difference': price_difference
                        }
                        logger.info(
                            f"✅ {service_name} purchase successful at ${actual_cost} (Ring4 unavailable)")

                    return result
                else:
                    logger.warning(
                        f"⚠️ {service_name} failed: {result.get('message', 'Unknown error')}")
            except Exception as e:
                logger.error(f"❌ {service_name} exception: {str(e)}")
                continue

        # If all services failed
        logger.error("❌ All SMS services failed")
        return {
            'success': False,
            'message': 'All SMS services are currently unavailable. Please try again later.',
            'price_warning': None
        }

    async def _purchase_sms_service(self, service_id: int, service_name: str) -> Dict[str, Any]:
        """Internal method to purchase from a specific SMS service with enhanced error handling"""
        if not self.api_key or self.api_key.strip() == "":
            return {'success': False, 'message': 'API key not configured'}

        url = f"{self.base_url}/purchase/sms"
        params = {
            'key': self.api_key,
            'service': service_id,
            'country': 1,  # USA
            'pool': ''  # Auto-select best pool
        }

        logger.info(
            f"🔄 Attempting {service_name} purchase (Service: {service_id})")

        try:
            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                async with session.get(url, params=params) as response:
                    logger.info(
                        f"📡 {service_name} API response status: {response.status}")

                    if response.status == 200:
                        try:
                            data = await response.json()
                            logger.info(f"📊 {service_name} response: {data}")
                        except json.JSONDecodeError as json_error:
                            text_data = await response.text()
                            logger.error(
                                f"❌ JSON decode error from {service_name}: {json_error}")
                            logger.debug(f"Raw response: {text_data[:200]}...")

                            # Try to extract useful info from HTML response
                            clean_text = re.sub(r'<[^>]+>', '', text_data)
                            clean_text = ' '.join(clean_text.split())
                            if 'out of stock' in clean_text.lower() or 'unavailable' in clean_text.lower():
                                return {'success': False, 'message': f'{service_name} service temporarily unavailable'}
                            return {'success': False, 'message': f'Invalid response format from {service_name}'}
                        except Exception as parse_error:
                            logger.error(
                                f"❌ Response parsing error from {service_name}: {parse_error}")
                            return {'success': False, 'message': f'Unable to parse response from {service_name}'}

                        # Enhanced success case validation
                        if isinstance(data, dict) and data.get('success') == 1:
                            order_id = data.get('order_id')
                            number = data.get('number')

                            # Validate essential fields
                            if not order_id:
                                logger.error(
                                    f"❌ {service_name} success response missing order_id")
                                return {'success': False, 'message': f'{service_name} response incomplete - missing order ID'}

                            if not number:
                                logger.warning(
                                    f"⚠️ {service_name} success response missing number")
                                # Some services might not return number immediately, but order_id is essential

                            logger.info(
                                f"✅ {service_name} number purchased: {number} (Order: {order_id})")
                            return {
                                'success': True,
                                'order_id': str(order_id),
                                'number': str(number) if number else 'Pending',
                                'cost': str(data.get('cost', '0.15')),
                                'service': service_name,
                                'country': 'US'
                            }
                        else:
                            # Parse error message
                            raw_error_msg = data.get(
                                'message', 'Unknown error')
                            clean_message = re.sub(
                                r'<[^>]+>', '', raw_error_msg)
                            clean_message = ' '.join(clean_message.split())

                            if 'couldn\'t find an available phone number' in clean_message or 'out of stock' in clean_message.lower():
                                error_msg = f'{service_name} service temporarily unavailable'
                            elif 'country & service you have selected is not valid' in clean_message:
                                error_msg = f'{service_name} service not available in this region'
                            else:
                                error_msg = clean_message[:100] + \
                                    ('...' if len(clean_message) > 100 else '')

                            logger.warning(
                                f"⚠️ {service_name} purchase failed: {error_msg}")
                            return {'success': False, 'message': error_msg}

                    elif response.status == 422:
                        # Handle SMSPool specific error responses
                        try:
                            data = await response.json()

                            # Parse SMSPool's complex error structure
                            if 'pools' in data:
                                balance_errors = []
                                for pool_name, pool_data in data['pools'].items():
                                    if pool_data.get('type') == 'BALANCE_ERROR':
                                        balance_errors.append(
                                            f"{pool_name}: {pool_data.get('message', 'Insufficient balance')}")
                                if balance_errors:
                                    error_msg = f"Insufficient balance across all pools: {'; '.join(balance_errors[:2])}"
                                    return {'success': False, 'message': error_msg}

                            raw_error_msg = data.get(
                                'message', 'Service unavailable')
                            clean_message = re.sub(
                                r'<[^>]+>', '', raw_error_msg)
                            clean_message = ' '.join(clean_message.split())

                            if 'couldn\'t find an available phone number' in clean_message or 'out of stock' in clean_message.lower():
                                error_msg = f'{service_name} service temporarily unavailable'
                            elif 'country & service you have selected is not valid' in clean_message:
                                error_msg = f'{service_name} service not available in this region'
                            else:
                                error_msg = clean_message[:100] + \
                                    ('...' if len(clean_message) > 100 else '')

                            return {'success': False, 'message': error_msg}

                        except:
                            html_text = await response.text()
                            clean_message = re.sub(r'<[^>]+>', '', html_text)
                            clean_message = ' '.join(clean_message.split())

                            if 'couldn\'t find an available phone number' in clean_message or 'out of stock' in clean_message.lower():
                                error_msg = f'{service_name} service temporarily unavailable'
                            elif 'country & service you have selected is not valid' in clean_message:
                                error_msg = f'{service_name} service not available in this region'
                            else:
                                error_msg = clean_message[:100] + \
                                    ('...' if len(clean_message) > 100 else '')

                            return {'success': False, 'message': error_msg}

                    else:
                        # Handle other HTTP errors
                        try:
                            data = await response.json()
                            error_msg = data.get(
                                'message', f'HTTP {response.status} error')
                        except:
                            html_text = await response.text()
                            clean_message = re.sub(r'<[^>]+>', '', html_text)
                            clean_message = ' '.join(clean_message.split())
                            error_msg = clean_message[:100] + \
                                ('...' if len(clean_message) > 100 else '')

                        logger.error(
                            f"❌ {service_name} purchase failed (HTTP {response.status}): {error_msg}")
                        return {'success': False, 'message': error_msg}

        except aiohttp.ClientConnectorError as conn_error:
            logger.error(
                f"❌ Connection error during {service_name} purchase: {conn_error}")
            return {'success': False, 'message': f'Unable to connect to SMSPool API for {service_name}'}
        except aiohttp.ServerTimeoutError:
            logger.error(f"❌ Timeout during {service_name} purchase")
            return {'success': False, 'message': f'Request timeout for {service_name} - API is responding slowly'}
        except aiohttp.ClientResponseError as resp_error:
            logger.error(
                f"❌ Response error during {service_name} purchase: {resp_error}")
            return {'success': False, 'message': f'Server error for {service_name}: HTTP {resp_error.status}'}
        except Exception as e:
            logger.error(f"❌ {service_name} API request failed: {str(e)}")
            error_type = type(e).__name__
            return {'success': False, 'message': f'Network error ({error_type}): {str(e)}'}

    async def check_service_availability(self, service_id: int = 1574, country_id: int = 1) -> Dict[str, Any]:
        """Check if service is available and get current pricing"""
        url = f"{self.base_url}/request/price"
        params = {
            'key': self.api_key,
            'service': service_id,
            'country': country_id
        }

        logger.info(
            f"🔍 Checking service availability (Service: {service_id}, Country: {country_id})")

        try:
            timeout = aiohttp.ClientTimeout(total=15)
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                async with session.get(url, params=params) as response:
                    logger.info(
                        f"📡 Service check API response status: {response.status}")

                    if response.status == 200:
                        try:
                            data = await response.json()
                            logger.info(f"📊 Service check response: {data}")

                            # Handle different response formats
                            if isinstance(data, dict) and 'price' in data:
                                price = data.get('price', 'Unknown')
                                # If price is 0 or empty, service might be unavailable
                                if price == 0 or price == '0' or not price:
                                    return {
                                        'success': False,
                                        'available': False,
                                        'price': '0',
                                        'message': 'Service temporarily unavailable (no pricing)'
                                    }
                                return {
                                    'success': True,
                                    'available': True,
                                    'price': str(price),
                                    'message': f'Service is available at ${price}'
                                }
                            elif isinstance(data, (int, float)) and data > 0:
                                # Sometimes API returns just the price as a number
                                return {
                                    'success': True,
                                    'available': True,
                                    'price': str(data),
                                    'message': f'Service is available at ${data}'
                                }
                            else:
                                return {
                                    'success': False,
                                    'available': False,
                                    'price': '0',
                                    'message': 'Service unavailable - invalid pricing response'
                                }
                        except:
                            text_data = await response.text()
                            logger.error(
                                f"❌ Non-JSON service check response: {text_data[:200]}...")

                            # Check if response is just a number (price)
                            try:
                                price = float(text_data.strip())
                                if price > 0:
                                    return {
                                        'success': True,
                                        'available': True,
                                        'price': str(price),
                                        'message': f'Service is available at ${price}'
                                    }
                                else:
                                    return {
                                        'success': False,
                                        'available': False,
                                        'price': '0',
                                        'message': 'Service temporarily unavailable (price is 0)'
                                    }
                            except ValueError:
                                return {
                                    'success': False,
                                    'available': False,
                                    'price': '0',
                                    'message': 'Invalid response format from service check'
                                }
                    else:
                        return {
                            'success': False,
                            'available': False,
                            'price': '0',
                            'message': f'Service check failed (HTTP {response.status})'
                        }
        except Exception as e:
            logger.error(f"❌ Service availability check failed: {str(e)}")
            return {
                'success': False,
                'available': False,
                'price': '0',
                'message': f'Network error: {str(e)}'
            }

    async def get_service_pricing(self, services: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Get current pricing for multiple services"""
        if services is None:
            services = [
                {'id': 1574, 'name': 'Ring4'},
                {'id': 22, 'name': 'Telegram'},
                {'id': 395, 'name': 'Google'},
                {'id': 1012, 'name': 'WhatsApp'},
            ]

        pricing_info = []
        available_services = []

        for service in services:
            service_id = service['id']
            service_name = service['name']

            # Check availability and pricing
            # US country
            availability = await self.check_service_availability(service_id, 1)

            pricing_data = {
                'id': service_id,
                'name': service_name,
                'available': availability.get('available', False),
                'price': availability.get('price', '0'),
                'message': availability.get('message', 'Unknown status')
            }

            pricing_info.append(pricing_data)

            if availability.get('available'):
                available_services.append(pricing_data)

        # Find cheapest available service
        cheapest_service = None
        if available_services:
            cheapest_service = min(
                available_services, key=lambda x: float(x['price']))

        return {
            'success': True,
            'all_services': pricing_info,
            'available_services': available_services,
            'cheapest_available': cheapest_service,
            'ring4_status': next((s for s in pricing_info if s['id'] == 1574), None)
        }

    async def get_available_services_for_purchase(self) -> Dict[str, Any]:
        """Get available services with selling prices for user selection"""
        from src.config import Config

        services_to_check = Config.SERVICE_PRIORITY
        available_services = []

        logger.info("🔍 Checking service availability for purchase menu...")

        for service in services_to_check:
            service_id = service['id']
            service_name = service['name']
            service_description = service['description']

            # Check availability and pricing
            # US country
            availability = await self.check_service_availability(service_id, 1)

            if availability.get('available'):
                api_price = float(availability.get('price', '0'))
                if api_price > 0:
                    selling_price = Config.calculate_selling_price(api_price)
                    profit = Config.get_profit_amount(api_price)

                    service_info = {
                        'id': service_id,
                        'name': service_name,
                        'description': service_description,
                        'api_price': api_price,
                        'selling_price': selling_price,
                        'profit': profit,
                        'available': True,
                        'recommended': service_id == 1574  # Ring4 is preferred
                    }
                    available_services.append(service_info)
                    logger.info(
                        f"✅ {service_name}: ${api_price} → ${selling_price} (profit: ${profit})")
                else:
                    logger.warning(
                        f"⚠️ {service_name}: Available but no valid pricing")
            else:
                logger.warning(
                    f"❌ {service_name}: {availability.get('message', 'Unavailable')}")

        # Sort by preference (Ring4 first, then by price)
        available_services.sort(key=lambda x: (
            not x['recommended'], x['selling_price']))

        return {
            'success': True,
            'services': available_services,
            'count': len(available_services),
            'profit_margin': Config.PROFIT_MARGIN_PERCENT
        }

    async def _check_service_purchase_availability(self, service_id: int, service_name: str) -> Dict[str, Any]:
        """Check if a specific service is available for purchase by checking active services"""
        if not self.api_key or self.api_key.strip() == "":
            return {'available': False, 'message': 'API key not configured'}

        logger.info(
            f"🔍 Checking {service_name} availability (Service: {service_id})")

        try:
            # Get list of available services to check if this specific service is available
            services_result = await self.get_available_services_for_purchase()

            if not services_result.get('success', False):
                return {'available': False, 'message': f'Unable to check {service_name} availability'}

            services = services_result.get('services', [])

            # Look for the specific service in the available services list
            for service in services:
                if service.get('id') == service_id:
                    # Service is in the list, so it should be available
                    return {'available': True, 'message': f'{service_name} is available for purchase'}

            # Service not found in available services list
            return {'available': False, 'message': f'{service_name} service temporarily unavailable'}

        except Exception as e:
            logger.error(
                f"❌ Unexpected error during {service_name} availability check: {str(e)}")
            return {'available': False, 'message': f'Unexpected error checking {service_name} availability'}

    async def purchase_specific_service(self, service_id: int, service_name: str) -> Dict[str, Any]:
        """Purchase a specific service by ID with pricing info"""
        from src.config import Config

        logger.info(f"🛒 Purchasing {service_name} (ID: {service_id})")

        try:
            result = await self._purchase_sms_service(service_id, service_name)

            if result.get('success'):
                # Add pricing information
                api_cost = float(result.get('cost', '0'))
                selling_price = Config.calculate_selling_price(api_cost)
                profit = Config.get_profit_amount(api_cost)

                result.update({
                    'api_cost': api_cost,
                    'selling_price': selling_price,
                    'profit': profit,
                    'service_selected': service_name
                })

                logger.info(
                    f"✅ {service_name} purchased: API=${api_cost}, Selling=${selling_price}, Profit=${profit}")

            return result
        except Exception as e:
            logger.error(f"❌ Error purchasing {service_name}: {str(e)}")
            return {
                'success': False,
                'message': f'Error purchasing {service_name}: {str(e)}'
            }

    async def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Check order status and SMS content with enhanced error handling"""
        if not self.api_key or self.api_key.strip() == "":
            return {
                'success': False,
                'status': 'error',
                'sms': None,
                'message': 'API key not configured'
            }

        if not order_id or order_id.strip() == "":
            return {
                'success': False,
                'status': 'error',
                'sms': None,
                'message': 'Order ID is required'
            }

        url = f"{self.base_url}/sms/check"
        params = {
            'key': self.api_key,
            'orderid': order_id.strip()
        }

        try:
            timeout = aiohttp.ClientTimeout(total=15)
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        try:
                            data = await response.json()
                            status = data.get('status', 'unknown')
                            sms_content = data.get('sms', None)

                            # Map numeric status codes to string values (SMSPool API documentation)
                            # Fixed status mapping based on actual SMSPool behavior
                            status_mapping = {
                                1: 'pending',      # SMS not received yet
                                2: 'success',      # SMS received successfully
                                # SMS dispatched/processing (NOT cancelled!)
                                3: 'processing',
                                4: 'expired',      # Order expired
                                5: 'timeout',      # Order timed out
                                6: 'cancelled',    # Order cancelled/refunded
                                'pending': 'pending',
                                'success': 'success',
                                'processing': 'processing',
                                'cancelled': 'cancelled',
                                'expired': 'expired',
                                'timeout': 'timeout'
                            }

                            # Convert numeric status to string if needed
                            if isinstance(status, (int, str)):
                                mapped_status = status_mapping.get(
                                    status, f'unknown_{status}')
                                if mapped_status != status:
                                    logger.info(
                                        f"🔄 Mapped status {status} -> {mapped_status}")
                                status = mapped_status

                            # Validate final status values
                            valid_statuses = [
                                'pending', 'success', 'processing', 'cancelled', 'expired', 'timeout']
                            if status not in valid_statuses and not status.startswith('unknown_'):
                                logger.warning(
                                    f"⚠️ Unexpected order status received: {status}")
                                status = f'unknown_{status}'

                            return {
                                'success': True,
                                'status': status,
                                'sms': sms_content,
                                'message': 'Order status retrieved successfully'
                            }
                        except json.JSONDecodeError as json_error:
                            logger.error(
                                f"❌ Failed to parse order status JSON: {json_error}")
                            text_response = await response.text()
                            logger.debug(
                                f"Raw response: {text_response[:200]}...")
                            return {
                                'success': False,
                                'status': 'error',
                                'sms': None,
                                'message': 'Invalid response format from order status API'
                            }
                    elif response.status == 404:
                        return {
                            'success': False,
                            'status': 'not_found',
                            'sms': None,
                            'message': f'Order {order_id} not found'
                        }
                    elif response.status == 401:
                        return {
                            'success': False,
                            'status': 'auth_error',
                            'sms': None,
                            'message': 'Invalid API key'
                        }
                    else:
                        try:
                            error_data = await response.json()
                            error_msg = error_data.get(
                                'message', f'HTTP {response.status} error')
                        except:
                            error_msg = f'Status check failed (HTTP {response.status})'
                        return {
                            'success': False,
                            'status': 'error',
                            'sms': None,
                            'message': error_msg
                        }
        except aiohttp.ClientConnectorError as conn_error:
            logger.error(
                f"❌ Connection error during order status check: {conn_error}")
            return {
                'success': False,
                'status': 'network_error',
                'sms': None,
                'message': 'Unable to connect to SMSPool API'
            }
        except aiohttp.ServerTimeoutError:
            logger.error("❌ Timeout during order status check")
            return {
                'success': False,
                'status': 'timeout',
                'sms': None,
                'message': 'Request timeout - API is responding slowly'
            }
        except Exception as e:
            logger.error(
                f"❌ Unexpected error during order status check: {str(e)}")
            return {
                'success': False,
                'status': 'error',
                'sms': None,
                'message': f'Network error: {str(e)}'
            }

    async def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order and request refund

        Note: SMSPool may not have a direct cancel endpoint. This method attempts
        multiple approaches and always returns success for user refund processing.
        """

        # Try multiple potential cancel endpoints
        cancel_attempts = [
            {
                'url': f"{self.base_url}/request/cancel",
                'params': {'key': self.api_key, 'orderid': order_id},
                'method': 'GET'
            },
            {
                'url': f"{self.base_url}/sms/cancel",
                'params': {'key': self.api_key, 'orderid': order_id},
                'method': 'GET'
            },
            {
                'url': f"{self.base_url}/purchase/cancel",
                'params': {'key': self.api_key, 'orderid': order_id},
                'method': 'POST'
            },
            {
                'url': f"{self.base_url}/stubs/handler_api",
                'params': {'api_key': self.api_key, 'action': '8', 'id': order_id},
                'method': 'GET'
            }
        ]

        successful_cancellation = False
        api_responses = []

        try:
            timeout = aiohttp.ClientTimeout(total=15)
            connector = aiohttp.TCPConnector(ssl=False)

            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                for attempt in cancel_attempts:
                    try:
                        if attempt['method'] == 'GET':
                            async with session.get(attempt['url'], params=attempt['params']) as response:
                                status = response.status
                                if status == 200:
                                    try:
                                        data = await response.json()
                                        api_responses.append(
                                            f"{attempt['url']}: {data}")

                                        # Check for success indicators
                                        if (data.get('success') == 1 or
                                            data.get('success') == True or
                                                'cancel' in str(data).lower()):
                                            successful_cancellation = True
                                            break

                                    except:
                                        text_data = await response.text()
                                        api_responses.append(
                                            f"{attempt['url']}: {text_data}")

                                        # Check for SMS-activate style success
                                        if text_data.strip() == "ACCESS_CANCEL":
                                            successful_cancellation = True
                                            break
                                else:
                                    api_responses.append(
                                        f"{attempt['url']}: HTTP {status}")

                        else:  # POST
                            async with session.post(attempt['url'], data=attempt['params']) as response:
                                status = response.status
                                if status == 200:
                                    try:
                                        data = await response.json()
                                        api_responses.append(
                                            f"{attempt['url']} (POST): {data}")

                                        if (data.get('success') == 1 or
                                                data.get('success') == True):
                                            successful_cancellation = True
                                            break
                                    except:
                                        text_data = await response.text()
                                        api_responses.append(
                                            f"{attempt['url']} (POST): {text_data}")
                                else:
                                    api_responses.append(
                                        f"{attempt['url']} (POST): HTTP {status}")

                    except Exception as e:
                        api_responses.append(
                            f"{attempt['url']}: Error - {str(e)}")
                        continue

        except Exception as e:
            api_responses.append(f"Session error: {str(e)}")

        # Log all attempts for debugging
        logger.info(f"🔄 Cancel attempts for order {order_id}:")
        for response in api_responses:
            logger.info(f"  📡 {response}")

        if successful_cancellation:
            logger.info(f"✅ Order {order_id} successfully cancelled via API")
            return {
                'success': True,
                'message': 'Order cancelled successfully via SMSPool API',
                'api_cancelled': True,
                'api_responses': api_responses
            }
        else:
            # Even if API cancel fails, we still process user refund
            # This is common practice - user gets refunded regardless of provider API status
            logger.warning(
                f"⚠️ API cancel failed for order {order_id}, but user refund will be processed")
            return {
                'success': True,  # Still return success for user refund processing
                'message': 'Order marked for cancellation - user refund will be processed',
                'api_cancelled': False,
                'api_responses': api_responses,
                'note': 'API cancellation failed but user refund guaranteed'
            }
