package com.hometracker.ingestion_service.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.PositiveOrZero;
import lombok.Builder;

import java.time.Instant;

@Builder
public record EnergyUsageDto (
        @NotNull(message = "Device ID is required")
        Long deviceId,
        @PositiveOrZero(message = "Energy consumed must be zero or positive")
        double energyConsumed,
        @NotNull(message = "Timestamp is required")
        @JsonFormat(shape = JsonFormat.Shape.STRING)
        Instant timestamp) {}