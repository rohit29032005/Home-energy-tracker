package com.hometracker.ingestion_service.service;

import com.hometracker.ingestion_service.dto.EnergyUsageDto;
import com.hometracker.ingestion_service.security.IngestionAuthorizationService;
import com.hometracker.kafka.event.EnergyUsageEvent;
import jakarta.servlet.http.HttpServletRequest;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

@Service
@Slf4j
public class IngestionService {

    private final KafkaTemplate<String, EnergyUsageEvent> kafkaTemplate;
    private final IngestionAuthorizationService ingestionAuthorizationService;

    public IngestionService(KafkaTemplate<String, EnergyUsageEvent> kafkaTemplate,
                            IngestionAuthorizationService ingestionAuthorizationService) {
        this.kafkaTemplate = kafkaTemplate;
        this.ingestionAuthorizationService = ingestionAuthorizationService;
    }

    public void ingestEnergyUsage(EnergyUsageDto input, HttpServletRequest request) {
        ingestionAuthorizationService.authorize(input, request);
        // Convert DTO to Event
        EnergyUsageEvent event = EnergyUsageEvent.builder()
                .deviceId(input.deviceId())
                .energyConsumed(input.energyConsumed())
                .timestamp(input.timestamp())
                .build();

        // Send to Kafka Topic
        kafkaTemplate.send("energy-usage", event);
        log.info("Ingested Energy Usage Event: {}", event);
    }
}
