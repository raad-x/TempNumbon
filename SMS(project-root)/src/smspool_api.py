import aiohttp
import logging
import re
import json
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


# Popular countries at the top for easy access
POPULAR_COUNTRIES = [
    {"id": 1, "name": "United States", "code": "US", "flag": "🇺🇸"},
    {"id": 2, "name": "United Kingdom", "code": "GB", "flag": "🇬🇧"},
    {"id": 3, "name": "Canada", "code": "CA", "flag": "🇨🇦"},
    {"id": 7, "name": "France", "code": "FR", "flag": "🇫🇷"},
    {"id": 9, "name": "Germany", "code": "DE", "flag": "🇩🇪"},
    {"id": 16, "name": "Netherlands", "code": "NL", "flag": "🇳🇱"},
    {"id": 22, "name": "Australia", "code": "AU", "flag": "🇦🇺"},
    {"id": 32, "name": "Sweden", "code": "SE", "flag": "🇸🇪"},
    {"id": 33, "name": "Norway", "code": "NO", "flag": "🇳🇴"},
    {"id": 38, "name": "Poland", "code": "PL", "flag": "🇵🇱"},
]


# Full country list with SMSPool country IDs
ALL_COUNTRIES = [
    {"id": 1, "name": "United States", "code": "US", "flag": "🇺🇸"},
    {"id": 2, "name": "United Kingdom", "code": "GB", "flag": "🇬🇧"},
    {"id": 3, "name": "Canada", "code": "CA", "flag": "🇨🇦"},
    {"id": 4, "name": "Israel", "code": "IL", "flag": "🇮🇱"},
    {"id": 5, "name": "Russia", "code": "RU", "flag": "🇷🇺"},
    {"id": 6, "name": "Ukraine", "code": "UA", "flag": "🇺🇦"},
    {"id": 7, "name": "France", "code": "FR", "flag": "🇫🇷"},
    {"id": 8, "name": "Kazakhstan", "code": "KZ", "flag": "🇰🇿"},
    {"id": 9, "name": "Germany", "code": "DE", "flag": "🇩🇪"},
    {"id": 10, "name": "China", "code": "CN", "flag": "🇨🇳"},
    {"id": 11, "name": "Belarus", "code": "BY", "flag": "🇧🇾"},
    {"id": 12, "name": "Kyrgyzstan", "code": "KG", "flag": "🇰🇬"},
    {"id": 13, "name": "Latvia", "code": "LV", "flag": "🇱🇻"},
    {"id": 14, "name": "Moldova", "code": "MD", "flag": "🇲🇩"},
    {"id": 15, "name": "Estonia", "code": "EE", "flag": "🇪🇪"},
    {"id": 16, "name": "Netherlands", "code": "NL", "flag": "🇳🇱"},
    {"id": 17, "name": "Lithuania", "code": "LT", "flag": "🇱🇹"},
    {"id": 18, "name": "Georgia", "code": "GE", "flag": "🇬🇪"},
    {"id": 19, "name": "Romania", "code": "RO", "flag": "🇷🇴"},
    {"id": 20, "name": "Uzbekistan", "code": "UZ", "flag": "🇺🇿"},
    {"id": 21, "name": "Croatia", "code": "HR", "flag": "🇭🇷"},
    {"id": 22, "name": "Australia", "code": "AU", "flag": "🇦🇺"},
    {"id": 23, "name": "Armenia", "code": "AM", "flag": "🇦🇲"},
    {"id": 24, "name": "Azerbaijan", "code": "AZ", "flag": "🇦🇿"},
    {"id": 25, "name": "Spain", "code": "ES", "flag": "🇪🇸"},
    {"id": 26, "name": "Italy", "code": "IT", "flag": "🇮🇹"},
    {"id": 27, "name": "Bulgaria", "code": "BG", "flag": "🇧🇬"},
    {"id": 28, "name": "Czech Republic", "code": "CZ", "flag": "🇨🇿"},
    {"id": 29, "name": "Finland", "code": "FI", "flag": "🇫🇮"},
    {"id": 30, "name": "Hungary", "code": "HU", "flag": "🇭🇺"},
    {"id": 31, "name": "Denmark", "code": "DK", "flag": "🇩🇰"},
    {"id": 32, "name": "Sweden", "code": "SE", "flag": "🇸🇪"},
    {"id": 33, "name": "Norway", "code": "NO", "flag": "🇳🇴"},
    {"id": 34, "name": "Austria", "code": "AT", "flag": "🇦🇹"},
    {"id": 35, "name": "Belgium", "code": "BE", "flag": "🇧🇪"},
    {"id": 36, "name": "Slovenia", "code": "SI", "flag": "🇸🇮"},
    {"id": 37, "name": "Slovakia", "code": "SK", "flag": "🇸🇰"},
    {"id": 38, "name": "Poland", "code": "PL", "flag": "🇵🇱"},
    {"id": 39, "name": "Greece", "code": "GR", "flag": "🇬🇷"},
    {"id": 40, "name": "Switzerland", "code": "CH", "flag": "🇨🇭"},
    {"id": 41, "name": "Portugal", "code": "PT", "flag": "🇵🇹"},
    {"id": 42, "name": "Ireland", "code": "IE", "flag": "🇮🇪"},
    {"id": 43, "name": "Luxembourg", "code": "LU", "flag": "🇱🇺"},
    {"id": 44, "name": "Malta", "code": "MT", "flag": "🇲🇹"},
    {"id": 45, "name": "Iceland", "code": "IS", "flag": "🇮🇸"},
    {"id": 46, "name": "Albania", "code": "AL", "flag": "🇦🇱"},
    {"id": 47, "name": "Montenegro", "code": "ME", "flag": "🇲🇪"},
    {"id": 48, "name": "Serbia", "code": "RS", "flag": "🇷🇸"},
    {"id": 49, "name": "Bosnia and Herzegovina", "code": "BA", "flag": "🇧🇦"},
    {"id": 50, "name": "North Macedonia", "code": "MK", "flag": "🇲🇰"},
    {"id": 51, "name": "Turkey", "code": "TR", "flag": "🇹🇷"},
    {"id": 52, "name": "Cyprus", "code": "CY", "flag": "🇨🇾"},
    {"id": 53, "name": "Japan", "code": "JP", "flag": "🇯🇵"},
    {"id": 54, "name": "South Korea", "code": "KR", "flag": "🇰🇷"},
    {"id": 55, "name": "India", "code": "IN", "flag": "🇮🇳"},
    {"id": 56, "name": "Thailand", "code": "TH", "flag": "🇹🇭"},
    {"id": 57, "name": "Vietnam", "code": "VN", "flag": "🇻🇳"},
    {"id": 58, "name": "Philippines", "code": "PH", "flag": "🇵🇭"},
    {"id": 59, "name": "Indonesia", "code": "ID", "flag": "🇮🇩"},
    {"id": 60, "name": "Malaysia", "code": "MY", "flag": "🇲🇾"},
    {"id": 61, "name": "Singapore", "code": "SG", "flag": "🇸🇬"},
    {"id": 62, "name": "Bangladesh", "code": "BD", "flag": "🇧🇩"},
    {"id": 63, "name": "Pakistan", "code": "PK", "flag": "🇵🇰"},
    {"id": 64, "name": "Sri Lanka", "code": "LK", "flag": "🇱🇰"},
    {"id": 65, "name": "Myanmar", "code": "MM", "flag": "🇲🇲"},
    {"id": 66, "name": "Cambodia", "code": "KH", "flag": "🇰🇭"},
    {"id": 67, "name": "Laos", "code": "LA", "flag": "🇱🇦"},
    {"id": 68, "name": "Nepal", "code": "NP", "flag": "🇳🇵"},
    {"id": 69, "name": "Bhutan", "code": "BT", "flag": "🇧🇹"},
    {"id": 70, "name": "Maldives", "code": "MV", "flag": "🇲🇻"},
    {"id": 71, "name": "Hong Kong", "code": "HK", "flag": "🇭🇰"},
    {"id": 72, "name": "Macau", "code": "MO", "flag": "🇲🇴"},
    {"id": 73, "name": "Taiwan", "code": "TW", "flag": "🇹🇼"},
    {"id": 74, "name": "Brazil", "code": "BR", "flag": "🇧🇷"},
    {"id": 75, "name": "Mexico", "code": "MX", "flag": "🇲🇽"},
    {"id": 76, "name": "Argentina", "code": "AR", "flag": "🇦🇷"},
    {"id": 77, "name": "Chile", "code": "CL", "flag": "🇨🇱"},
    {"id": 78, "name": "Colombia", "code": "CO", "flag": "🇨🇴"},
    {"id": 79, "name": "Peru", "code": "PE", "flag": "🇵🇪"},
    {"id": 80, "name": "Venezuela", "code": "VE", "flag": "🇻🇪"},
    {"id": 81, "name": "Ecuador", "code": "EC", "flag": "🇪🇨"},
    {"id": 82, "name": "Bolivia", "code": "BO", "flag": "🇧🇴"},
    {"id": 83, "name": "Paraguay", "code": "PY", "flag": "🇵🇾"},
    {"id": 84, "name": "Uruguay", "code": "UY", "flag": "🇺🇾"},
    {"id": 85, "name": "Guyana", "code": "GY", "flag": "🇬🇾"},
    {"id": 86, "name": "Suriname", "code": "SR", "flag": "🇸🇷"},
    {"id": 87, "name": "French Guiana", "code": "GF", "flag": "🇬🇫"},
    {"id": 88, "name": "South Africa", "code": "ZA", "flag": "🇿🇦"},
    {"id": 89, "name": "Egypt", "code": "EG", "flag": "🇪🇬"},
    {"id": 90, "name": "Nigeria", "code": "NG", "flag": "🇳🇬"},
    {"id": 91, "name": "Kenya", "code": "KE", "flag": "🇰🇪"},
    {"id": 92, "name": "Ghana", "code": "GH", "flag": "🇬🇭"},
    {"id": 93, "name": "Morocco", "code": "MA", "flag": "🇲🇦"},
    {"id": 94, "name": "Algeria", "code": "DZ", "flag": "🇩🇿"},
    {"id": 95, "name": "Tunisia", "code": "TN", "flag": "🇹🇳"},
    {"id": 96, "name": "Libya", "code": "LY", "flag": "🇱🇾"},
    {"id": 97, "name": "Sudan", "code": "SD", "flag": "🇸🇩"},
    {"id": 98, "name": "Ethiopia", "code": "ET", "flag": "🇪🇹"},
    {"id": 99, "name": "Uganda", "code": "UG", "flag": "🇺🇬"},
    {"id": 100, "name": "Tanzania", "code": "TZ", "flag": "🇹🇿"},
]


class SMSPoolAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.smspool.net"

    def get_countries_list(self, popular_only: bool = False) -> List[Dict[str, Any]]:
        """Get list of available countries"""
        if popular_only:
            return POPULAR_COUNTRIES.copy()
        return ALL_COUNTRIES.copy()

    def search_countries(self, query: str) -> List[Dict[str, Any]]:
        """Search countries by name or code"""
        query = query.lower().strip()
        if not query:
            return self.get_countries_list(popular_only=True)

        results = []
        for country in ALL_COUNTRIES:
            if (query in country["name"].lower() or
                    query in country["code"].lower()):
                results.append(country)

        # Limit results to prevent overwhelming UI
        return results[:15]

    def get_country_by_id(self, country_id: int) -> Optional[Dict[str, Any]]:
        """Get country details by ID"""
        for country in ALL_COUNTRIES:
            if country["id"] == country_id:
                return country
        return None

    def get_country_by_code(self, country_code: str) -> Optional[Dict[str, Any]]:
        """Get country details by country code"""
        country_code = country_code.upper().strip()
        for country in ALL_COUNTRIES:
            if country["code"] == country_code:
                return country
        return None

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
                'message': 'Unable to connect to SMS Bot API - please check your internet connection'
            }
        except aiohttp.ServerTimeoutError:
            logger.error("❌ Timeout during balance check")
            return {
                'success': False,
                'balance': '0',
                'message': 'Request timeout - SMS Bot API is responding slowly'
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

        # Get country info for logging
        country = self.get_country_by_id(country_id)
        country_name = country["name"] if country else f"Country ID {country_id}"

        logger.info(f"🌍 Target country: {country_name} (ID: {country_id})")

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
                f"🔄 Attempting {service_name} (ID: {service_id}, expected: ${expected_price}) for {country_name}")

            try:
                result = await self._purchase_sms_service(service_id, service_name, country_id)
                if result.get('success'):
                    # Calculate price warning
                    actual_cost = float(result.get('cost', expected_price))

                    if service_name == 'Ring4':
                        # Ring4 worked, no warning needed
                        result['price_warning'] = None
                        logger.info(
                            f"✅ Ring4 purchase successful at ${actual_cost} for {country_name}")
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
                            f"✅ {service_name} purchase successful at ${actual_cost} for {country_name} (Ring4 unavailable)")

                    # Add country info to result
                    result['country'] = country_name
                    result['country_id'] = country_id
                    return result
                else:
                    logger.warning(
                        f"⚠️ {service_name} failed for {country_name}: {result.get('message', 'Unknown error')}")
            except Exception as e:
                logger.error(
                    f"❌ {service_name} exception for {country_name}: {str(e)}")
                continue

        # If all services failed
        logger.error(f"❌ All SMS services failed for {country_name}")
        return {
            'success': False,
            'message': f'All SMS services are currently unavailable for {country_name}. Please try again later.',
            'price_warning': None,
            'country': country_name,
            'country_id': country_id
        }

    async def _purchase_sms_service(self, service_id: int, service_name: str, country_id: int = 1) -> Dict[str, Any]:
        """Internal method to purchase from a specific SMS service with enhanced error handling"""
        if not self.api_key or self.api_key.strip() == "":
            return {'success': False, 'message': 'API key not configured'}

        url = f"{self.base_url}/purchase/sms"
        params = {
            'key': self.api_key,
            'service': service_id,
            'country': country_id,  # Use the provided country_id
            'pool': ''  # Auto-select best pool
        }

        # Get country info for logging
        country = self.get_country_by_id(country_id)
        country_name = country["name"] if country else f"Country ID {country_id}"

        logger.info(
            f"🔄 Attempting {service_name} purchase (Service: {service_id}, Country: {country_name})")

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
                                f"✅ {service_name} number purchased: {number} (Order: {order_id}) for {country_name}")
                            return {
                                'success': True,
                                'order_id': str(order_id),
                                'number': str(number) if number else 'Pending',
                                'cost': str(data.get('cost', '0.15')),
                                'service': service_name,
                                'country': country_name,
                                'country_id': country_id
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
            return {'success': False, 'message': f'Unable to connect to SMS Bot API for {service_name}'}
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

    async def get_service_pricing(self, services: Optional[List[Dict[str, Any]]] = None, country_id: int = 1) -> Dict[str, Any]:
        """Get current pricing for multiple services in a specific country"""
        if services is None:
            services = [
                {'id': 1574, 'name': 'Ring4'},
                {'id': 22, 'name': 'Telegram'},
                {'id': 395, 'name': 'Google'},
                {'id': 1012, 'name': 'WhatsApp'},
            ]

        # Get country info
        country = self.get_country_by_id(country_id)
        country_name = country["name"] if country else f"Country ID {country_id}"

        pricing_info = []
        available_services = []

        logger.info(f"🔍 Checking service pricing for {country_name}")

        for service in services:
            service_id = service['id']
            service_name = service['name']

            # Check availability and pricing for the specified country
            availability = await self.check_service_availability(service_id, country_id)

            pricing_data = {
                'id': service_id,
                'name': service_name,
                'available': availability.get('available', False),
                'price': availability.get('price', '0'),
                'message': availability.get('message', 'Unknown status'),
                'country': country_name,
                'country_id': country_id
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
            'ring4_status': next((s for s in pricing_info if s['id'] == 1574), None),
            'country': country_name,
            'country_id': country_id
        }

    async def get_available_services_for_purchase(self, country_id: int = 1) -> Dict[str, Any]:
        """Get available services with selling prices for user selection in specified country"""
        from src.config import Config

        services_to_check = Config.SERVICE_PRIORITY
        available_services = []

        # Get country info
        country = self.get_country_by_id(country_id)
        country_name = country["name"] if country else f"Country ID {country_id}"

        logger.info(
            f"🔍 Checking service availability for purchase menu in {country_name}...")

        for service in services_to_check:
            service_id = service['id']
            service_name = service['name']
            service_description = service['description']
            # Get service key for fixed pricing
            service_key = service.get('service_key')

            # Check availability and pricing for the specified country
            availability = await self.check_service_availability(service_id, country_id)

            if availability.get('available'):
                api_price = float(availability.get('price', '0'))
                if api_price > 0:
                    selling_price = Config.calculate_selling_price(
                        api_price, service_key)
                    profit = Config.get_profit_amount(api_price)

                    service_info = {
                        'id': service_id,
                        'name': service_name,
                        'description': service_description,
                        'api_price': api_price,
                        'selling_price': selling_price,
                        'profit': profit,
                        'available': True,
                        'recommended': service_id == 1574,  # Ring4 is preferred
                        'country': country_name,
                        'country_id': country_id
                    }
                    available_services.append(service_info)
                    logger.info(
                        f"✅ {service_name} in {country_name}: ${api_price} → ${selling_price} (profit: ${profit})")
                else:
                    logger.warning(
                        f"⚠️ {service_name} in {country_name}: Available but no valid pricing")
            else:
                logger.warning(
                    f"❌ {service_name} in {country_name}: {availability.get('message', 'Unavailable')}")

        # Sort by preference (Ring4 first, then by price)
        available_services.sort(key=lambda x: (
            not x['recommended'], x['selling_price']))

        return {
            'success': True,
            'services': available_services,
            'count': len(available_services),
            'profit_margin': Config.PROFIT_MARGIN_PERCENT,
            'country': country_name,
            'country_id': country_id
        }

    async def _check_service_purchase_availability(self, service_id: int, service_name: str, country_id: int = 1) -> Dict[str, Any]:
        """Check if a specific service is available for purchase by checking active services"""
        if not self.api_key or self.api_key.strip() == "":
            return {'available': False, 'message': 'API key not configured'}

        # Get country info
        country = self.get_country_by_id(country_id)
        country_name = country["name"] if country else f"Country ID {country_id}"

        logger.info(
            f"🔍 Checking {service_name} availability in {country_name} (Service: {service_id})")

        try:
            # Get list of available services to check if this specific service is available
            services_result = await self.get_available_services_for_purchase(country_id)

            if not services_result.get('success', False):
                return {'available': False, 'message': f'Unable to check {service_name} availability in {country_name}'}

            services = services_result.get('services', [])

            # Look for the specific service in the available services list
            for service in services:
                if service.get('id') == service_id:
                    # Service is in the list, so it should be available
                    return {'available': True, 'message': f'{service_name} is available for purchase in {country_name}'}

            # Service not found in available services list
            return {'available': False, 'message': f'{service_name} service temporarily unavailable in {country_name}'}

        except Exception as e:
            logger.error(
                f"❌ Unexpected error during {service_name} availability check in {country_name}: {str(e)}")
            return {'available': False, 'message': f'Unexpected error checking {service_name} availability in {country_name}'}

    async def purchase_specific_service(self, service_id: int, service_name: str, country_id: int = 1) -> Dict[str, Any]:
        """Purchase a specific service by ID with pricing info for specified country"""
        from src.config import Config

        # Get country info
        country = self.get_country_by_id(country_id)
        country_name = country["name"] if country else f"Country ID {country_id}"

        logger.info(
            f"🛒 Purchasing {service_name} (ID: {service_id}) in {country_name}")

        try:
            result = await self._purchase_sms_service(service_id, service_name, country_id)

            if result.get('success'):
                # Add pricing information
                api_cost = float(result.get('cost', '0'))
                service_key = Config.get_service_key_by_id(service_id)
                selling_price = Config.calculate_selling_price(
                    api_cost, service_key)
                profit = Config.get_profit_amount(api_cost)

                result.update({
                    'api_cost': api_cost,
                    'selling_price': selling_price,
                    'profit': profit,
                    'service_selected': service_name,
                    'country': country_name,
                    'country_id': country_id
                })

                logger.info(
                    f"✅ {service_name} purchased in {country_name}: API=${api_cost}, Selling=${selling_price}, Profit=${profit}")

            return result
        except Exception as e:
            logger.error(
                f"❌ Error purchasing {service_name} in {country_name}: {str(e)}")
            return {
                'success': False,
                'message': f'Error purchasing {service_name} in {country_name}: {str(e)}',
                'country': country_name,
                'country_id': country_id
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
                'message': 'Unable to connect to SMS Bot API'
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
        """Cancel an order and request refund using correct SMS Pool API endpoints

        Based on API testing, SMS Pool uses /sms/cancel endpoint with key and orderid parameters.
        Returns: {'success': 1, 'message': 'The order has been successfully archived.'} on success
        """

        # Use the correct SMS Pool cancel endpoint with POST method
        url = f"{self.base_url}/sms/cancel"
        data = {'key': self.api_key, 'orderid': order_id}

        try:
            timeout = aiohttp.ClientTimeout(total=15)
            connector = aiohttp.TCPConnector(ssl=False)

            async with aiohttp.ClientSession(timeout=timeout, connector=connector) as session:
                try:
                    async with session.post(url, data=data) as response:
                        status = response.status

                        if status == 200:
                            try:
                                data = await response.json()

                                # Check for successful cancellation
                                if data.get('success') == 1:
                                    logger.info(
                                        f"✅ Order {order_id} successfully cancelled via SMSPool API")
                                    return {
                                        'success': True,
                                        'message': f"Order cancelled successfully: {data.get('message', 'Order archived')}",
                                        'api_cancelled': True,
                                        'api_response': data
                                    }
                                elif data.get('success') == 0:
                                    # API returned error - log details but still process user refund
                                    error_messages = []
                                    if 'errors' in data:
                                        for error in data['errors']:
                                            error_messages.append(
                                                error.get('message', 'Unknown error'))

                                    error_text = '; '.join(
                                        error_messages) if error_messages else 'Unknown API error'
                                    logger.warning(
                                        f"⚠️ SMSPool API cancel failed for order {order_id}: {error_text}")

                                    return {
                                        'success': True,  # Still process user refund
                                        'message': f'API cancellation failed ({error_text}) but user refund will be processed',
                                        'api_cancelled': False,
                                        'api_response': data,
                                        'note': 'User refund guaranteed despite API failure'
                                    }
                                else:
                                    # Unexpected response format
                                    logger.warning(
                                        f"⚠️ Unexpected SMSPool API response for order {order_id}: {data}")
                                    return {
                                        'success': True,  # Still process user refund
                                        'message': 'Unexpected API response format - user refund will be processed',
                                        'api_cancelled': False,
                                        'api_response': data,
                                        'note': 'User refund guaranteed despite unexpected response'
                                    }

                            except Exception as json_error:
                                # Failed to parse JSON response
                                text_data = await response.text()
                                logger.warning(
                                    f"⚠️ Failed to parse SMSPool API response for order {order_id}: {json_error}")
                                logger.info(f"Raw response: {text_data}")

                                return {
                                    'success': True,  # Still process user refund
                                    'message': 'API response parsing failed - user refund will be processed',
                                    'api_cancelled': False,
                                    'raw_response': text_data,
                                    'note': 'User refund guaranteed despite parsing failure'
                                }
                        else:
                            # Non-200 HTTP status
                            logger.warning(
                                f"⚠️ SMSPool API returned HTTP {status} for order {order_id}")
                            return {
                                'success': True,  # Still process user refund
                                'message': f'API returned HTTP {status} - user refund will be processed',
                                'api_cancelled': False,
                                'http_status': status,
                                'note': 'User refund guaranteed despite HTTP error'
                            }

                except Exception as request_error:
                    logger.warning(
                        f"⚠️ Request error during SMSPool API cancel for order {order_id}: {request_error}")
                    return {
                        'success': True,  # Still process user refund
                        'message': f'Connection error ({str(request_error)}) - user refund will be processed',
                        'api_cancelled': False,
                        'error': str(request_error),
                        'note': 'User refund guaranteed despite connection error'
                    }

        except Exception as e:
            logger.error(
                f"❌ Critical error during SMSPool API cancel for order {order_id}: {str(e)}")
            return {
                'success': True,  # Always process user refund regardless of API issues
                'message': f'Critical error ({str(e)}) - user refund will be processed',
                'api_cancelled': False,
                'error': str(e),
                'note': 'User refund guaranteed despite critical error'
            }
