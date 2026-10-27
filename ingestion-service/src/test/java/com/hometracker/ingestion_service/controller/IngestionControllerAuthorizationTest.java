package com.hometracker.ingestion_service.controller;

import com.hometracker.ingestion_service.exception.GlobalExceptionHandler;
import com.hometracker.ingestion_service.service.IngestionService;
import jakarta.servlet.http.HttpServletRequest;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.web.server.ResponseStatusException;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.setup.MockMvcBuilders.standaloneSetup;

class IngestionControllerAuthorizationTest {

    private IngestionService ingestionService;
    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        ingestionService = mock(IngestionService.class);
        mockMvc = standaloneSetup(new IngestionController(ingestionService))
                .setControllerAdvice(new GlobalExceptionHandler())
                .build();
    }

    @Test
    void returnsUnauthorizedInsteadOfInternalServerErrorForInvalidDeviceToken() throws Exception {
        rejectWith(HttpStatus.UNAUTHORIZED, "A device-bound telemetry credential is required for this device");

        mockMvc.perform(validReading())
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.status").value(401))
                .andExpect(jsonPath("$.message")
                        .value("A device-bound telemetry credential is required for this device"));
    }

    @Test
    void returnsForbiddenInsteadOfInternalServerErrorForCrossOwnerTelemetry() throws Exception {
        rejectWith(HttpStatus.FORBIDDEN, "The authenticated user does not own the telemetry device");

        mockMvc.perform(validReading())
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.status").value(403))
                .andExpect(jsonPath("$.message")
                        .value("The authenticated user does not own the telemetry device"));
    }

    private void rejectWith(HttpStatus status, String reason) {
        doThrow(new ResponseStatusException(status, reason))
                .when(ingestionService)
                .ingestEnergyUsage(any(), any(HttpServletRequest.class));
    }

    private static org.springframework.test.web.servlet.request.MockHttpServletRequestBuilder validReading() {
        return post("/api/v1/ingestion")
                .contentType(MediaType.APPLICATION_JSON)
                .content("""
                        {"deviceId":1,"energyConsumed":0.25,"timestamp":"2026-01-01T00:00:00Z"}
                        """);
    }
}
