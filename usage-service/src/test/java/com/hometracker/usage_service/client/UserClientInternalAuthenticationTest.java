package com.hometracker.usage_service.client;

import com.hometracker.usage_service.dto.UserDto;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

class UserClientInternalAuthenticationTest {

    @Test
    void sendsInternalServiceTokenWhenLookingUpAUser() {
        RestTemplate restTemplate = new RestTemplate();
        MockRestServiceServer server = MockRestServiceServer.bindTo(restTemplate).build();
        UserClient client = new UserClient(
                restTemplate,
                "http://user-service/api/v1/user",
                "usage-service-test-token");

        server.expect(requestTo("http://user-service/api/v1/user/7"))
                .andExpect(method(org.springframework.http.HttpMethod.GET))
                .andExpect(header("X-Internal-Service-Token", "usage-service-test-token"))
                .andRespond(withSuccess("""
                        {"id":7,"name":"Demo","surname":"User","email":"demo@example.com","address":"123 Smart Energy St","alerting":true,"energyAlertingThreshold":25.0}
                        """, MediaType.APPLICATION_JSON));

        UserDto user = client.getUserById(7L);

        assertEquals(7L, user.id());
        assertEquals("demo@example.com", user.email());
        server.verify();
    }
}
