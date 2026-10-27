package com.hometracker.usage_service.service;

import com.influxdb.client.InfluxDBClient;
import com.influxdb.client.WriteApiBlocking;
import com.hometracker.kafka.event.AlertingEvent;
import com.hometracker.kafka.event.EnergyUsageEvent;
import com.hometracker.usage_service.client.DeviceClient;
import com.hometracker.usage_service.client.UserClient;
import com.hometracker.usage_service.exception.InfluxWriteException;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.test.util.ReflectionTestUtils;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Instant;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class UsageServiceInfluxWriteTest {

    @Mock
    private InfluxDBClient influxDBClient;

    @Mock
    private WriteApiBlocking writeApi;

    @Mock
    private DeviceClient deviceClient;

    @Mock
    private UserClient userClient;

    @Mock
    private KafkaTemplate<String, AlertingEvent> kafkaTemplate;

    private UsageService usageService;

    @BeforeEach
    void setUp() {
        usageService = new UsageService(influxDBClient, deviceClient, userClient, kafkaTemplate);
        ReflectionTestUtils.setField(usageService, "influxBucket", "usage-bucket");
        ReflectionTestUtils.setField(usageService, "influxOrg", "hometracker");
    }

    @Test
    void writesAValidKafkaEventToInflux() {
        when(influxDBClient.getWriteApiBlocking()).thenReturn(writeApi);

        usageService.energyUsageEvent(reading());

        verify(writeApi).writePoint(eq("usage-bucket"), eq("hometracker"), any());
    }

    @Test
    void propagatesAnInfluxFailureSoKafkaCanRetryOrDeadLetterTheRecord() {
        IllegalStateException writeFailure = new IllegalStateException("Influx unavailable");
        when(influxDBClient.getWriteApiBlocking()).thenReturn(writeApi);
        doThrow(writeFailure).when(writeApi).writePoint(eq("usage-bucket"), eq("hometracker"), any());

        InfluxWriteException exception = assertThrows(InfluxWriteException.class,
                () -> usageService.energyUsageEvent(reading()));

        assertEquals("Unable to persist energy usage event", exception.getMessage());
        assertSame(writeFailure, exception.getCause());
        verify(writeApi).writePoint(eq("usage-bucket"), eq("hometracker"), any());
    }

    private static EnergyUsageEvent reading() {
        return EnergyUsageEvent.builder()
                .deviceId(1L)
                .energyConsumed(0.25)
                .timestamp(Instant.parse("2026-01-01T00:00:00Z"))
                .build();
    }
}
