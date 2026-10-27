package com.hometracker.ingestion_service.service;

import com.hometracker.ingestion_service.dto.EnergyUsageDto;
import com.hometracker.ingestion_service.security.IngestionAuthorizationService;
import com.hometracker.kafka.event.EnergyUsageEvent;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;

class IngestionServiceAuthorizationTest {

    @Test
    void doesNotPublishToKafkaWhenAuthorizationFails() {
        KafkaTemplate<String, EnergyUsageEvent> kafkaTemplate = mock(KafkaTemplate.class);
        IngestionAuthorizationService authorizer = mock(IngestionAuthorizationService.class);
        IngestionService service = new IngestionService(kafkaTemplate, authorizer);
        doThrow(new ResponseStatusException(HttpStatus.FORBIDDEN))
                .when(authorizer).authorize(any(), any());

        assertThrows(ResponseStatusException.class,
                () -> service.ingestEnergyUsage(reading(), new MockHttpServletRequest()));

        verifyNoInteractions(kafkaTemplate);
    }

    @Test
    void publishesOnlyAfterAuthorizationSucceeds() {
        KafkaTemplate<String, EnergyUsageEvent> kafkaTemplate = mock(KafkaTemplate.class);
        IngestionAuthorizationService authorizer = mock(IngestionAuthorizationService.class);
        IngestionService service = new IngestionService(kafkaTemplate, authorizer);

        assertDoesNotThrow(() -> service.ingestEnergyUsage(reading(), new MockHttpServletRequest()));

        verify(authorizer).authorize(any(), any());
        verify(kafkaTemplate).send(eq("energy-usage"), any(EnergyUsageEvent.class));
    }

    private EnergyUsageDto reading() {
        return EnergyUsageDto.builder()
                .deviceId(1L)
                .energyConsumed(0.25)
                .timestamp(Instant.parse("2026-01-01T00:00:00Z"))
                .build();
    }
}
