import http from 'k6/http';
import { check, sleep } from 'k6';

const baseUrl = __ENV.BASE_URL || 'http://localhost:8080';
const deviceToken = __ENV.WOKWI_INGESTION_TOKEN;
if (!deviceToken) throw new Error('WOKWI_INGESTION_TOKEN must be supplied to k6.');

export const options = {
  scenarios: {
    progressive_ingestion: {
      executor: 'ramping-arrival-rate',
      startRate: 1,
      timeUnit: '1s',
      preAllocatedVUs: 10,
      maxVUs: 50,
      stages: [
        { target: 2, duration: '30s' },
        { target: 5, duration: '30s' },
        { target: 10, duration: '30s' },
        { target: 0, duration: '15s' }
      ]
    }
  },
  thresholds: {
    http_req_failed: ['rate<0.05'],
    http_req_duration: ['p(95)<2000']
  }
};

export default function () {
  const payload = JSON.stringify({
    deviceId: 1,
    energyConsumed: 0.2 + Math.random() * 0.1,
    timestamp: new Date().toISOString()
  });
  const response = http.post(`${baseUrl}/api/v1/ingestion`, payload, {
    headers: { 'Content-Type': 'application/json', 'X-Device-Token': deviceToken, 'X-Correlation-ID': `k6-${__VU}-${__ITER}` },
    tags: { endpoint: 'ingestion' }
  });
  check(response, { 'ingestion accepted': value => value.status === 201 });
  sleep(0.1);
}
