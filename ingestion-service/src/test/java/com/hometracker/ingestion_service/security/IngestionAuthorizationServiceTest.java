package com.hometracker.ingestion_service.security;

import com.hometracker.ingestion_service.dto.EnergyUsageDto;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.server.ResponseStatusException;

import java.time.Instant;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.springframework.test.web.client.ExpectedCount.once;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;

class IngestionAuthorizationServiceTest {

    @Test
    void permitsAuthenticatedOwnerOnlyAfterDeviceServiceConfirmsOwnership() {
        RestTemplate restTemplate = new RestTemplate();
        MockRestServiceServer server = MockRestServiceServer.bindTo(restTemplate).build();
        IngestionAuthorizationService authorizer = authorizer(restTemplate, "1:token-for-device-1");
        MockHttpServletRequest request = requestWithOwner("1");

        server.expect(once(), requestTo("http://device-service:8082/api/v1/device/1"))
                .andExpect(method(org.springframework.http.HttpMethod.GET))
                .andExpect(header(IngestionAuthorizationService.AUTHENTICATED_USER_HEADER, "1"))
                .andExpect(header(IngestionAuthorizationService.GATEWAY_AUTHORIZATION_HEADER,
                        "gateway-proof"))
                .andRespond(withStatus(HttpStatus.OK).contentType(MediaType.APPLICATION_JSON).body("{}"));

        assertDoesNotThrow(() -> authorizer.authorize(reading(1L), request));
        server.verify();
    }

    @Test
    void rejectsAuthenticatedUserWhenDeviceServiceRejectsOwnership() {
        RestTemplate restTemplate = new RestTemplate();
        MockRestServiceServer server = MockRestServiceServer.bindTo(restTemplate).build();
        IngestionAuthorizationService authorizer = authorizer(restTemplate, "1:token-for-device-1");

        server.expect(requestTo("http://device-service:8082/api/v1/device/2"))
                .andRespond(withStatus(HttpStatus.FORBIDDEN));

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> authorizer.authorize(reading(2L), requestWithOwner("1")));

        assertEquals(HttpStatus.FORBIDDEN, exception.getStatusCode());
        server.verify();
    }

    @Test
    void permitsOnlyTheTokenMappedToTheRequestedDevice() {
        IngestionAuthorizationService authorizer = authorizer(new RestTemplate(),
                "1:token-for-device-1,2:token-for-device-2");
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader(IngestionAuthorizationService.DEVICE_TOKEN_HEADER, "token-for-device-2");

        assertDoesNotThrow(() -> authorizer.authorize(reading(2L), request));
    }

    @Test
    void rejectsAValidDeviceTokenWhenThePayloadClaimsAnotherDevice() {
        IngestionAuthorizationService authorizer = authorizer(new RestTemplate(),
                "1:token-for-device-1,2:token-for-device-2");
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader(IngestionAuthorizationService.DEVICE_TOKEN_HEADER, "token-for-device-1");

        ResponseStatusException exception = assertThrows(ResponseStatusException.class,
                () -> authorizer.authorize(reading(2L), request));

        assertEquals(HttpStatus.UNAUTHORIZED, exception.getStatusCode());
    }

    @Test
    void rejectsAConfigurationThatReusesOneTokenForMultipleDevices() {
        IllegalArgumentException exception = assertThrows(IllegalArgumentException.class,
                () -> new IngestionAuthorizationService(new RestTemplate(), true,
                        "http://device-service:8082/api/v1/device",
                        "1:shared-token,2:shared-token", false, "", "gateway-proof"));

        assertEquals("Device token mapping must not reuse a token across multiple devices",
                exception.getMessage());
    }

    @Test
    void rejectsUserIdentityWithoutAMatchingGatewayProofBeforeCallingDeviceService() {
        RestTemplate restTemplate = new RestTemplate();
        MockRestServiceServer server = MockRestServiceServer.bindTo(restTemplate).build();
        IngestionAuthorizationService authorizer = authorizer(restTemplate, "1:token-for-device-1");

        MockHttpServletRequest missingProof = new MockHttpServletRequest();
        missingProof.addHeader(IngestionAuthorizationService.AUTHENTICATED_USER_HEADER, "1");
        ResponseStatusException missingProofException = assertThrows(ResponseStatusException.class,
                () -> authorizer.authorize(reading(1L), missingProof));
        assertEquals(HttpStatus.UNAUTHORIZED, missingProofException.getStatusCode());

        MockHttpServletRequest forgedProof = new MockHttpServletRequest();
        forgedProof.addHeader(IngestionAuthorizationService.AUTHENTICATED_USER_HEADER, "1");
        forgedProof.addHeader(IngestionAuthorizationService.GATEWAY_AUTHORIZATION_HEADER, "forged-proof");
        ResponseStatusException forgedProofException = assertThrows(ResponseStatusException.class,
                () -> authorizer.authorize(reading(1L), forgedProof));
        assertEquals(HttpStatus.UNAUTHORIZED, forgedProofException.getStatusCode());

        server.verify();
    }

    @Test
    void rejectsAnEnabledConfigurationWithoutTheGatewayProof() {
        IllegalStateException exception = assertThrows(IllegalStateException.class,
                () -> new IngestionAuthorizationService(new RestTemplate(), true,
                        "http://device-service:8082/api/v1/device",
                        "1:token-for-device-1", false, "", ""));

        assertEquals("Telemetry authorization is enabled but no gateway-to-ingestion proof is configured",
                exception.getMessage());
    }

    private IngestionAuthorizationService authorizer(RestTemplate restTemplate, String deviceTokens) {
        return new IngestionAuthorizationService(restTemplate, true,
                "http://device-service:8082/api/v1/device", deviceTokens, false, "", "gateway-proof");
    }

    private MockHttpServletRequest requestWithOwner(String userId) {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader(IngestionAuthorizationService.AUTHENTICATED_USER_HEADER, userId);
        request.addHeader(IngestionAuthorizationService.GATEWAY_AUTHORIZATION_HEADER, "gateway-proof");
        return request;
    }

    private EnergyUsageDto reading(Long deviceId) {
        return EnergyUsageDto.builder()
                .deviceId(deviceId)
                .energyConsumed(0.25)
                .timestamp(Instant.parse("2026-01-01T00:00:00Z"))
                .build();
    }
}
