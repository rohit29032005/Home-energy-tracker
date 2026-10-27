package com.hometracker.insight_service.controller;

import com.hometracker.insight_service.dto.BillForecastDto;
import com.hometracker.insight_service.dto.InsightDto;
import com.hometracker.insight_service.exception.GlobalExceptionHandler;
import com.hometracker.insight_service.security.GatewayOwnershipVerifier;
import com.hometracker.insight_service.service.InsightService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.request.MockMvcRequestBuilders;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.util.List;

import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@ExtendWith(MockitoExtension.class)
class InsightControllerAuthorizationTest {

    private static final String GATEWAY_PROOF = "gateway-proof";

    @Mock
    private InsightService insightService;

    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        mockMvc = MockMvcBuilders
                .standaloneSetup(new InsightController(
                        insightService, new GatewayOwnershipVerifier(GATEWAY_PROOF)))
                .setControllerAdvice(new GlobalExceptionHandler())
                .build();
    }

    @Test
    void rejectsUnauthenticatedRequestsForEveryInsightEndpointBeforeServiceInvocation() throws Exception {
        List<String> endpoints = List.of(
                "/api/v1/insight/saving-tips/7",
                "/api/v1/insight/overview/7",
                "/api/v1/insight/bill-forecast/7?days=3",
                "/api/v1/insight/appliance-ranking/7?days=3",
                "/api/v1/insight/standby-detective/7?days=3");

        for (String endpoint : endpoints) {
            mockMvc.perform(MockMvcRequestBuilders.get(endpoint))
                    .andExpect(status().isUnauthorized());
        }

        verifyNoInteractions(insightService);
    }

    @Test
    void rejectsAValidGatewayProofWhenTheOwnerDoesNotMatchThePath() throws Exception {
        mockMvc.perform(MockMvcRequestBuilders.get("/api/v1/insight/overview/8")
                        .header(GatewayOwnershipVerifier.GATEWAY_AUTHORIZATION_HEADER, GATEWAY_PROOF)
                        .header(GatewayOwnershipVerifier.AUTHENTICATED_USER_HEADER, "7"))
                .andExpect(status().isForbidden());

        verifyNoInteractions(insightService);
    }

    @Test
    void permitsAUserWhenGatewayProofAndOwnerMatch() throws Exception {
        when(insightService.getSavingsTips(7L)).thenReturn(InsightDto.builder()
                .userId(7L)
                .tips("Use less energy")
                .build());

        mockMvc.perform(MockMvcRequestBuilders.get("/api/v1/insight/saving-tips/7")
                        .header(GatewayOwnershipVerifier.GATEWAY_AUTHORIZATION_HEADER, GATEWAY_PROOF)
                        .header(GatewayOwnershipVerifier.AUTHENTICATED_USER_HEADER, "7"))
                .andExpect(status().isOk());

        verify(insightService).getSavingsTips(7L);
    }

    @Test
    void permitsAGatewayAuthorizedAdminRouteWithoutAnOwnerHeader() throws Exception {
        when(insightService.getBillForecast(11L, 2)).thenReturn(BillForecastDto.builder()
                .userId(11L)
                .periodDays(2)
                .build());

        mockMvc.perform(MockMvcRequestBuilders.get("/api/v1/insight/bill-forecast/11")
                        .param("days", "2")
                        .header(GatewayOwnershipVerifier.GATEWAY_AUTHORIZATION_HEADER, GATEWAY_PROOF))
                .andExpect(status().isOk());

        verify(insightService).getBillForecast(11L, 2);
    }
}
