package com.hometracker.alert_service.controller;

import com.hometracker.alert_service.security.AlertApiAuthorizationVerifier;
import com.hometracker.alert_service.service.AlertService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(
        controllers = AlertController.class,
        properties = {
                "security.internal.gateway-token=alert-gateway-proof",
                "internal.service.token=background-service-token"
        })
@Import(AlertApiAuthorizationVerifier.class)
class AlertControllerAuthorizationTest {

    private static final String GATEWAY_PROOF = "alert-gateway-proof";
    private static final String OWNER_HEADER = "X-Authenticated-User-Id";
    private static final String GATEWAY_HEADER = "X-Gateway-Authorization";
    private static final String SERVICE_HEADER = "X-Internal-Service-Token";
    private static final String SERVICE_TOKEN = "background-service-token";

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private AlertService alertService;

    @Test
    void userAlertRouteAllowsMatchingOwnerAndTrustedGatewayAdmin() throws Exception {
        when(alertService.getAlertsByUserId(7L)).thenReturn(List.of());

        mockMvc.perform(get("/api/v1/alert/user/7")
                        .header(GATEWAY_HEADER, GATEWAY_PROOF)
                        .header(OWNER_HEADER, "7"))
                .andExpect(status().isOk());

        mockMvc.perform(get("/api/v1/alert/user/7")
                        .header(GATEWAY_HEADER, GATEWAY_PROOF))
                .andExpect(status().isOk());

        verify(alertService, times(2)).getAlertsByUserId(7L);
    }

    @Test
    void userAlertRouteRejectsMissingForgedAndCrossOwnerCalls() throws Exception {
        mockMvc.perform(get("/api/v1/alert/user/7"))
                .andExpect(status().isUnauthorized());

        mockMvc.perform(get("/api/v1/alert/user/7")
                        .header(GATEWAY_HEADER, "forged-proof")
                        .header(OWNER_HEADER, "7"))
                .andExpect(status().isUnauthorized());

        mockMvc.perform(get("/api/v1/alert/user/7")
                        .header(GATEWAY_HEADER, GATEWAY_PROOF)
                        .header(OWNER_HEADER, "8"))
                .andExpect(status().isForbidden());

        verifyNoInteractions(alertService);
    }

    @Test
    void administrativeRoutesRequireTrustedGatewayAdmin() throws Exception {
        when(alertService.getAllAlerts()).thenReturn(List.of());

        mockMvc.perform(get("/api/v1/alert"))
                .andExpect(status().isUnauthorized());

        mockMvc.perform(get("/api/v1/alert")
                        .header(GATEWAY_HEADER, GATEWAY_PROOF)
                        .header(OWNER_HEADER, "7"))
                .andExpect(status().isForbidden());

        mockMvc.perform(get("/api/v1/alert")
                        .header(GATEWAY_HEADER, GATEWAY_PROOF))
                .andExpect(status().isOk());

        mockMvc.perform(post("/api/v1/alert/test-send")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(testEventJson())
                        .header(GATEWAY_HEADER, GATEWAY_PROOF)
                        .header(OWNER_HEADER, "7"))
                .andExpect(status().isForbidden());

        mockMvc.perform(post("/api/v1/alert/test-send")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(testEventJson())
                        .header(GATEWAY_HEADER, GATEWAY_PROOF))
                .andExpect(status().isOk());

        verify(alertService).getAllAlerts();
        verify(alertService).energyUsageAlertEvent(any());
    }

    @Test
    void backgroundServiceTokenIsNeverAcceptedByAlertHttpEndpoints() throws Exception {
        mockMvc.perform(get("/api/v1/alert")
                        .header(SERVICE_HEADER, SERVICE_TOKEN))
                .andExpect(status().isUnauthorized());

        mockMvc.perform(get("/api/v1/alert/user/7")
                        .header(SERVICE_HEADER, SERVICE_TOKEN))
                .andExpect(status().isUnauthorized());

        mockMvc.perform(post("/api/v1/alert/test-send")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(testEventJson())
                        .header(SERVICE_HEADER, SERVICE_TOKEN))
                .andExpect(status().isUnauthorized());

        mockMvc.perform(get("/api/v1/alert")
                        .header(GATEWAY_HEADER, GATEWAY_PROOF)
                        .header(SERVICE_HEADER, SERVICE_TOKEN))
                .andExpect(status().isUnauthorized());

        verifyNoInteractions(alertService);
    }

    private String testEventJson() {
        return """
                {
                  "userId": 7,
                  "deviceId": 12,
                  "message": "test alert",
                  "alertType": "THRESHOLD",
                  "threshold": 25.0,
                  "energyConsumed": 30.0,
                  "email": "owner@example.test"
                }
                """;
    }
}
