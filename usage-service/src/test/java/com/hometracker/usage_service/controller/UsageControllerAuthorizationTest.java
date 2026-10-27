package com.hometracker.usage_service.controller;

import com.hometracker.usage_service.dto.UsageDto;
import com.hometracker.usage_service.exception.GlobalExceptionHandler;
import com.hometracker.usage_service.security.UsageAccessVerifier;
import com.hometracker.usage_service.service.UsageService;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;

import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(UsageController.class)
@Import({UsageAccessVerifier.class, GlobalExceptionHandler.class})
@TestPropertySource(properties = {
        "security.internal.gateway-token=gateway-proof",
        "security.internal.service-token=internal-service-token"
})
class UsageControllerAuthorizationTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private UsageService usageService;

    @Test
    void rejectsARequestWithoutTrustedCallerCredentialsBeforeUsageLookup() throws Exception {
        mockMvc.perform(get("/api/v1/usage/7"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.status").value(401));

        verifyNoInteractions(usageService);
    }

    @Test
    void rejectsForgedAndSmuggledCredentialsBeforeUsageLookup() throws Exception {
        mockMvc.perform(get("/api/v1/usage/7")
                        .header(UsageAccessVerifier.GATEWAY_AUTHORIZATION_HEADER, "forged-gateway-proof")
                        .header(UsageAccessVerifier.AUTHENTICATED_USER_HEADER, "7"))
                .andExpect(status().isUnauthorized());

        mockMvc.perform(get("/api/v1/usage/7")
                        .header(UsageAccessVerifier.INTERNAL_SERVICE_TOKEN_HEADER,
                                "internal-service-token")
                        .header(UsageAccessVerifier.AUTHENTICATED_USER_HEADER, "7"))
                .andExpect(status().isUnauthorized());

        verifyNoInteractions(usageService);
    }

    @Test
    void rejectsAGatewayOwnerMismatchBeforeUsageLookup() throws Exception {
        mockMvc.perform(get("/api/v1/usage/8")
                        .header(UsageAccessVerifier.GATEWAY_AUTHORIZATION_HEADER, "gateway-proof")
                        .header(UsageAccessVerifier.AUTHENTICATED_USER_HEADER, "7"))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.status").value(403));

        verifyNoInteractions(usageService);
    }

    @Test
    void permitsAGatewayOwnerToReadTheirUsage() throws Exception {
        when(usageService.getXDaysUsageForUser(7L, 3)).thenReturn(usage(7L));

        mockMvc.perform(get("/api/v1/usage/7")
                        .header(UsageAccessVerifier.GATEWAY_AUTHORIZATION_HEADER, "gateway-proof")
                        .header(UsageAccessVerifier.AUTHENTICATED_USER_HEADER, "7"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.userId").value(7));

        verify(usageService).getXDaysUsageForUser(7L, 3);
    }

    @Test
    void permitsAGatewayAdministratorRouteWithoutAnOwnerHeader() throws Exception {
        when(usageService.getXDaysUsageForUser(7L, 5)).thenReturn(usage(7L));

        mockMvc.perform(get("/api/v1/usage/7")
                        .param("days", "5")
                        .header(UsageAccessVerifier.GATEWAY_AUTHORIZATION_HEADER, "gateway-proof"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.userId").value(7));

        verify(usageService).getXDaysUsageForUser(7L, 5);
    }

    @Test
    void permitsAHeaderCleanInternalInsightReadCaller() throws Exception {
        when(usageService.getXDaysUsageForUser(7L, 3)).thenReturn(usage(7L));

        mockMvc.perform(get("/api/v1/usage/7")
                        .header(UsageAccessVerifier.INTERNAL_SERVICE_TOKEN_HEADER,
                                "internal-service-token"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.userId").value(7));

        verify(usageService).getXDaysUsageForUser(eq(7L), eq(3));
    }

    private static UsageDto usage(Long userId) {
        return UsageDto.builder()
                .userId(userId)
                .devices(List.of())
                .build();
    }
}
