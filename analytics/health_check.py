"""
Health Check Script for Analytics Service Container
Performs health checks on the Python analytics service
"""

import asyncio
import sys
import os
import aiohttp
from datetime import datetime

# Configuration
HOST = os.getenv('HOST', 'localhost')
PORT = int(os.getenv('PORT', 8000))
TIMEOUT = int(os.getenv('HEALTH_CHECK_TIMEOUT', 5))

async def perform_health_check():
    """
    Performs async HTTP health check on the analytics service
    """
    url = f"http://{HOST}:{PORT}/health"
    
    try:
        timeout = aiohttp.ClientTimeout(total=TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    if data.get('status') == 'healthy':
                        print(f"Health check passed: {data}")
                        return True
                    else:
                        print(f"Health check failed: Service unhealthy - {data}")
                        return False
                else:
                    print(f"Health check failed: HTTP {response.status}")
                    return False
                    
    except asyncio.TimeoutError:
        print(f"Health check failed: Timeout after {TIMEOUT}s")
        return False
    except aiohttp.ClientError as e:
        print(f"Health check failed: Client error - {e}")
        return False
    except Exception as e:
        print(f"Health check failed: Unexpected error - {e}")
        return False

async def main():
    """Main health check execution"""
    print(f"Performing health check on analytics service at {HOST}:{PORT}")
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    
    success = await perform_health_check()
    
    if success:
        print("Analytics service health check: PASSED")
        sys.exit(0)
    else:
        print("Analytics service health check: FAILED")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())