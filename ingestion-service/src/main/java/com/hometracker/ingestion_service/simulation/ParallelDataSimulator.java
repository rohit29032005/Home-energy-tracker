package com.hometracker.ingestion_service.simulation;

import com.hometracker.ingestion_service.dto.EnergyUsageDto;
import com.hometracker.ingestion_service.security.IngestionAuthorizationService;
import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.time.ZoneId;
import java.util.Random;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ThreadPoolExecutor;

@Slf4j
@Component
@ConditionalOnProperty(name = "simulation.enabled", havingValue = "true")
public class ParallelDataSimulator implements CommandLineRunner {

    private final RestTemplate restTemplate;
    private final Random random;

    @Value("${simulation.parallel-threads}")
    private int parallelThreads;

    @Value("${simulation.requests-per-interval}")
    private int requestsPerInterval;

    @Value("${simulation.endpoint}")
    private String ingestionEndpoint;

    @Value("${simulation.device-id:1}")
    private long simulatedDeviceId;

    @Value("${simulation.device-token:}")
    private String deviceToken;

    private final ExecutorService executorService;

    public ParallelDataSimulator() {
        this(new RestTemplate(), new Random(), Executors.newCachedThreadPool());
    }

    ParallelDataSimulator(RestTemplate restTemplate, Random random, ExecutorService executorService) {
        this.restTemplate = restTemplate;
        this.random = random;
        this.executorService = executorService;
    }

    @Override
    public void run(String... args) throws Exception {
        log.info("ParallelDataSimulator started...");
        ((ThreadPoolExecutor)executorService).setCorePoolSize(parallelThreads);
    }

    @Scheduled(fixedRateString = "${simulation.interval-ms}")
    public void sendMockData() {
        int batchSize = requestsPerInterval / parallelThreads;
        int remainder = requestsPerInterval % parallelThreads;

        for (int i = 0; i < parallelThreads; i++) {
            int requestsForThread = batchSize + (i < remainder ? 1 : 0);
            executorService.submit(() -> {
                for (int j = 0; j < requestsForThread; j++) {
                    EnergyUsageDto dto = EnergyUsageDto.builder()
                            .deviceId(simulatedDeviceId)
                            .energyConsumed(Math.round(random.nextDouble(0.0, 2.0) * 100.0) / 100.0)
                            .timestamp(LocalDateTime.now()
                                    .atZone(ZoneId.systemDefault()).toInstant())
                            .build();
                    try {
                        HttpHeaders headers = new HttpHeaders();
                        headers.setContentType(MediaType.APPLICATION_JSON);
                        if (deviceToken != null && !deviceToken.isBlank()) {
                            headers.set(IngestionAuthorizationService.DEVICE_TOKEN_HEADER, deviceToken);
                        }
                        HttpEntity<EnergyUsageDto> request = new HttpEntity<>(dto, headers);
                        restTemplate.postForEntity(ingestionEndpoint, request, Void.class);
                        log.info("Sent mock data: " + dto);
                    } catch (Exception e) {
                        log.error("Failed to send data: " + e.getMessage());
                    }
                }
            });
        }
    }

    @PreDestroy
    public void shutdown() {
        executorService.shutdown();
        log.info("ParallelDataSimulator shut down.");
    }
}
