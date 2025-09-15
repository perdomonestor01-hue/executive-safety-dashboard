/**
 * Health Check Script for Docker Container
 * Performs health checks on the Executive Safety Dashboard application
 */

const http = require('http');
const process = require('process');

const HOST = process.env.HOST || 'localhost';
const PORT = process.env.PORT || 3000;
const TIMEOUT = parseInt(process.env.HEALTH_CHECK_TIMEOUT) || 5000;

/**
 * Performs HTTP health check
 */
function performHealthCheck() {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: HOST,
      port: PORT,
      path: '/health',
      method: 'GET',
      timeout: TIMEOUT
    };

    const req = http.request(options, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        if (res.statusCode === 200) {
          try {
            const response = JSON.parse(data);
            if (response.status === 'OK') {
              resolve(response);
            } else {
              reject(new Error(`Health check failed: ${response.status}`));
            }
          } catch (error) {
            reject(new Error(`Invalid JSON response: ${error.message}`));
          }
        } else {
          reject(new Error(`HTTP ${res.statusCode}: ${res.statusMessage}`));
        }
      });
    });

    req.on('error', (error) => {
      reject(new Error(`Request failed: ${error.message}`));
    });

    req.on('timeout', () => {
      req.destroy();
      reject(new Error(`Health check timeout after ${TIMEOUT}ms`));
    });

    req.setTimeout(TIMEOUT);
    req.end();
  });
}

/**
 * Main health check execution
 */
async function main() {
  try {
    console.log(`Performing health check on ${HOST}:${PORT}`);
    const result = await performHealthCheck();
    
    console.log('Health check passed:', {
      status: result.status,
      uptime: result.uptime,
      timestamp: result.timestamp
    });
    
    process.exit(0);
  } catch (error) {
    console.error('Health check failed:', error.message);
    process.exit(1);
  }
}

// Run health check if called directly
if (require.main === module) {
  main();
}

module.exports = { performHealthCheck };