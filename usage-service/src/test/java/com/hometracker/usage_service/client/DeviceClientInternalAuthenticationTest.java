package com.hometracker.usage_service.client;

import com.hometracker.usage_service.dto.DeviceDto;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

class DeviceClientInternalAuthenticationTest {

    private static final String INTERNAL_SERVICE_TOKEN = "usage-service-test-token";

    @Test
    void sendsInternalServiceTokenWhenLookingUpOneDevice() {
        RestTemplate restTemplate = new RestTemplate();
        MockRestServiceServer server = MockRestServiceServer.bindTo(restTemplate).build();
        DeviceClient client = new DeviceClient(restTemplate, "http://device-service/api/v1/device", INTERNAL_SERVICE_TOKEN);

        server.expect(requestTo("http://device-service/api/v1/device/42"))
                .andExpect(method(org.springframework.http.HttpMethod.GET))
                .andExpect(header("X-Internal-Service-Token", INTERNAL_SERVICE_TOKEN))
                .andRespond(withSuccess("""
                        {"id":42,"name":"Heat Pump","type":"HVAC","location":"Living room","userId":7,"energyConsumed":0.25}
                        """, MediaType.APPLICATION_JSON));

        DeviceDto device = client.getDeviceById(42L);

        assertEquals(42L, device.id());
        assertEquals(7L, device.userId());
        server.verify();
    }

    @Test
    void sendsInternalServiceTokenWhenLookingUpAUsersDevices() {
        RestTemplate restTemplate = new RestTemplate();
        MockRestServiceServer server = MockRestServiceServer.bindTo(restTemplate).build();
        DeviceClient client = new DeviceClient(restTemplate, "http://device-service/api/v1/device", INTERNAL_SERVICE_TOKEN);

        server.expect(requestTo("http://device-service/api/v1/device/user/7"))
                .andExpect(method(org.springframework.http.HttpMethod.GET))
                .andExpect(header("X-Internal-Service-Token", INTERNAL_SERVICE_TOKEN))
                .andRespond(withSuccess("""
                        [{"id":42,"name":"Heat Pump","type":"HVAC","location":"Living room","userId":7,"energyConsumed":0.25}]
                        """, MediaType.APPLICATION_JSON));

        List<DeviceDto> devices = client.getAllDevicesForUser(7L);

        assertEquals(1, devices.size());
        assertEquals(42L, devices.get(0).id());
        server.verify();
    }
}
