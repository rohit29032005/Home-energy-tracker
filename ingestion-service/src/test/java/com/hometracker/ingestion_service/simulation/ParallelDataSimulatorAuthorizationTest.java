package com.hometracker.ingestion_service.simulation;

import com.hometracker.ingestion_service.dto.EnergyUsageDto;
import com.hometracker.ingestion_service.security.IngestionAuthorizationService;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpEntity;
import org.springframework.web.client.RestTemplate;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Random;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.timeout;
import static org.mockito.Mockito.verify;
import static org.mockito.ArgumentCaptor.forClass;

class ParallelDataSimulatorAuthorizationTest {

    @Test
    void sendsTheConfiguredDeviceBoundTokenForTheConfiguredDeviceId() {
        RestTemplate restTemplate = mock(RestTemplate.class);
        ExecutorService executor = Executors.newSingleThreadExecutor();
        ParallelDataSimulator simulator = new ParallelDataSimulator(restTemplate, new Random(7), executor);
        ReflectionTestUtils.setField(simulator, "parallelThreads", 1);
        ReflectionTestUtils.setField(simulator, "requestsPerInterval", 1);
        ReflectionTestUtils.setField(simulator, "ingestionEndpoint", "http://ingestion-service:8083/api/v1/ingestion");
        ReflectionTestUtils.setField(simulator, "simulatedDeviceId", 1L);
        ReflectionTestUtils.setField(simulator, "deviceToken", "token-for-device-1");

        try {
            simulator.sendMockData();

            @SuppressWarnings("unchecked")
            var requestCaptor = forClass(HttpEntity.class);
            verify(restTemplate, timeout(1_000)).postForEntity(
                    eq("http://ingestion-service:8083/api/v1/ingestion"),
                    requestCaptor.capture(),
                    eq(Void.class));

            HttpEntity<?> request = requestCaptor.getValue();
            assertEquals("token-for-device-1",
                    request.getHeaders().getFirst(IngestionAuthorizationService.DEVICE_TOKEN_HEADER));
            assertEquals(1L, ((EnergyUsageDto) request.getBody()).deviceId());
        } finally {
            simulator.shutdown();
        }
    }
}
