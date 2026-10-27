package com.hometracker.alert_service.client;

import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

class AlertContextClientInternalAuthenticationTest {

    private static final String INTERNAL_SERVICE_TOKEN = "alert-service-test-token";

    @Test
    void getDeviceSendsTheConfiguredInternalServiceToken() {
        RestTemplate restTemplate = new RestTemplate();
        MockRestServiceServer server = MockRestServiceServer.bindTo(restTemplate).build();
        AlertContextClient client = new AlertContextClient(
                restTemplate,
                "http://device-service/api/v1/device",
                "http://user-service/api/v1/user",
                INTERNAL_SERVICE_TOKEN);

        server.expect(requestTo("http://device-service/api/v1/device/12"))
                .andExpect(method(org.springframework.http.HttpMethod.GET))
                .andExpect(header("X-Internal-Service-Token", INTERNAL_SERVICE_TOKEN))
                .andRespond(withSuccess("{\"id\":12,\"userId\":34}", MediaType.APPLICATION_JSON));

        AlertContextClient.DeviceReference device = client.getDevice(12L);

        assertEquals(12L, device.id());
        assertEquals(34L, device.userId());
        server.verify();
    }

    @Test
    void getUserSendsTheConfiguredInternalServiceToken() {
        RestTemplate restTemplate = new RestTemplate();
        MockRestServiceServer server = MockRestServiceServer.bindTo(restTemplate).build();
        AlertContextClient client = new AlertContextClient(
                restTemplate,
                "http://device-service/api/v1/device",
                "http://user-service/api/v1/user",
                INTERNAL_SERVICE_TOKEN);

        server.expect(requestTo("http://user-service/api/v1/user/34"))
                .andExpect(method(org.springframework.http.HttpMethod.GET))
                .andExpect(header("X-Internal-Service-Token", INTERNAL_SERVICE_TOKEN))
                .andRespond(withSuccess(
                        "{\"id\":34,\"email\":\"alert@example.com\",\"alerting\":true}",
                        MediaType.APPLICATION_JSON));

        AlertContextClient.UserReference user = client.getUser(34L);

        assertEquals(34L, user.id());
        assertEquals("alert@example.com", user.email());
        assertEquals(true, user.alerting());
        server.verify();
    }
}
