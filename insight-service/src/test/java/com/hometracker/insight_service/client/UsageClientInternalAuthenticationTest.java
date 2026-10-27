package com.hometracker.insight_service.client;

import com.hometracker.insight_service.dto.UsageDto;
import com.hometracker.insight_service.security.GatewayOwnershipVerifier;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.headerDoesNotExist;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

class UsageClientInternalAuthenticationTest {

    @Test
    void sendsOnlyTheInternalServiceCredentialToUsageService() {
        RestTemplate restTemplate = new RestTemplate();
        MockRestServiceServer server = MockRestServiceServer.bindTo(restTemplate).build();
        UsageClient client = new UsageClient(
                restTemplate,
                "http://usage-service/api/v1/usage",
                "insight-service-test-token");

        server.expect(requestTo("http://usage-service/api/v1/usage/7?days=3"))
                .andExpect(method(org.springframework.http.HttpMethod.GET))
                .andExpect(header(
                        GatewayOwnershipVerifier.INTERNAL_SERVICE_TOKEN_HEADER,
                        "insight-service-test-token"))
                .andExpect(headerDoesNotExist(
                        GatewayOwnershipVerifier.AUTHENTICATED_USER_HEADER))
                .andExpect(headerDoesNotExist(
                        GatewayOwnershipVerifier.GATEWAY_AUTHORIZATION_HEADER))
                .andRespond(withSuccess("""
                        {"userId":7,"devices":[]}
                        """, MediaType.APPLICATION_JSON));

        UsageDto usage = client.getXDaysUsageForUser(7L, 3);

        assertEquals(7L, usage.userId());
        assertEquals(0, usage.devices().size());
        server.verify();
    }
}
