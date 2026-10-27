package com.hometracker.device_service.controller;

import com.hometracker.device_service.dto.DeviceDto;
import com.hometracker.device_service.exception.GlobalExceptionHandler;
import com.hometracker.device_service.model.DeviceType;
import com.hometracker.device_service.security.OwnershipVerifier;
import com.hometracker.device_service.service.DeviceService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class DeviceControllerPrivateCallerTest {

    private static final String GATEWAY_TOKEN = "gateway-proof";
    private static final String SERVICE_TOKEN = "background-service-token";

    private DeviceService deviceService;
    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        deviceService = mock(DeviceService.class);
        OwnershipVerifier verifier = new OwnershipVerifier(GATEWAY_TOKEN, SERVICE_TOKEN);
        mockMvc = MockMvcBuilders
                .standaloneSetup(new DeviceController(deviceService, verifier))
                .setControllerAdvice(new GlobalExceptionHandler())
                .build();
    }

    @Test
    void rejectsDirectReadBeforeLookingUpTheDevice() throws Exception {
        mockMvc.perform(get("/api/v1/device/1"))
                .andExpect(status().isUnauthorized());

        verifyNoInteractions(deviceService);
    }

    @Test
    void rejectsForgedOwnerHeaderBeforeLookingUpTheDevice() throws Exception {
        mockMvc.perform(get("/api/v1/device/1")
                        .header(OwnershipVerifier.HEADER, "7"))
                .andExpect(status().isUnauthorized());

        verifyNoInteractions(deviceService);
    }

    @Test
    void rejectsGatewayOwnerMismatchAfterAuthenticatingTheGateway() throws Exception {
        DeviceDto device = DeviceDto.builder()
                .id(1L)
                .name("Meter")
                .type(DeviceType.LIGHT)
                .location("Kitchen")
                .userId(8L)
                .build();
        when(deviceService.getDeviceById(1L)).thenReturn(device);

        mockMvc.perform(get("/api/v1/device/1")
                        .header(OwnershipVerifier.GATEWAY_AUTHORIZATION_HEADER, GATEWAY_TOKEN)
                        .header(OwnershipVerifier.HEADER, "7"))
                .andExpect(status().isForbidden());

        verify(deviceService).getDeviceById(1L);
    }

    @Test
    void permitsReadOnlyBackgroundServiceRequestsWithTheServiceToken() throws Exception {
        DeviceDto device = DeviceDto.builder()
                .id(1L)
                .name("Meter")
                .type(DeviceType.LIGHT)
                .location("Kitchen")
                .userId(8L)
                .build();
        when(deviceService.getDeviceById(1L)).thenReturn(device);

        mockMvc.perform(get("/api/v1/device/1")
                        .header(OwnershipVerifier.INTERNAL_SERVICE_TOKEN_HEADER, SERVICE_TOKEN))
                .andExpect(status().isOk());

        verify(deviceService).getDeviceById(1L);
    }

    @Test
    void deniesBackgroundServicesFromCreatingDevices() throws Exception {
        String requestBody = """
                {"name":"Meter","type":"LIGHT","location":"Kitchen","userId":8}
                """;

        mockMvc.perform(post("/api/v1/device")
                        .header(OwnershipVerifier.INTERNAL_SERVICE_TOKEN_HEADER, SERVICE_TOKEN)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(requestBody))
                .andExpect(status().isUnauthorized());

        verifyNoInteractions(deviceService);
    }
}
