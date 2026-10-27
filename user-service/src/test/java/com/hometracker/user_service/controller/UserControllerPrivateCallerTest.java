package com.hometracker.user_service.controller;

import com.hometracker.user_service.dto.UserDto;
import com.hometracker.user_service.exception.GlobalExceptionHandler;
import com.hometracker.user_service.security.OwnershipVerifier;
import com.hometracker.user_service.service.UserService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class UserControllerPrivateCallerTest {

    private static final String GATEWAY_TOKEN = "gateway-proof";
    private static final String SERVICE_TOKEN = "background-service-token";

    private UserService userService;
    private MockMvc mockMvc;

    @BeforeEach
    void setUp() {
        userService = mock(UserService.class);
        OwnershipVerifier verifier = new OwnershipVerifier(GATEWAY_TOKEN, SERVICE_TOKEN);
        mockMvc = MockMvcBuilders
                .standaloneSetup(new UserController(userService, verifier))
                .setControllerAdvice(new GlobalExceptionHandler())
                .build();
    }

    @Test
    void rejectsDirectUserListRequestsBeforeCallingTheService() throws Exception {
        mockMvc.perform(get("/api/v1/user"))
                .andExpect(status().isUnauthorized());

        verifyNoInteractions(userService);
    }

    @Test
    void permitsReadOnlyBackgroundServiceRequestsWithTheServiceToken() throws Exception {
        UserDto user = UserDto.builder()
                .id(7L)
                .name("Demo")
                .surname("User")
                .email("demo@example.com")
                .address("Test Street")
                .alerting(true)
                .energyAlertingThreshold(25.0)
                .build();
        org.mockito.Mockito.when(userService.getUserById(7L)).thenReturn(user);

        mockMvc.perform(get("/api/v1/user/7")
                        .header(OwnershipVerifier.INTERNAL_SERVICE_TOKEN_HEADER, SERVICE_TOKEN))
                .andExpect(status().isOk());

        verify(userService).getUserById(7L);
    }

    @Test
    void deniesBackgroundServicesFromCreatingProfiles() throws Exception {
        String requestBody = """
                {"name":"Other","surname":"User","email":"other@example.com",
                 "address":"Test Street","alerting":true,"energyAlertingThreshold":25.0}
                """;

        mockMvc.perform(post("/api/v1/user")
                        .header(OwnershipVerifier.INTERNAL_SERVICE_TOKEN_HEADER, SERVICE_TOKEN)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(requestBody))
                .andExpect(status().isUnauthorized());

        verifyNoInteractions(userService);
    }

    @Test
    void rejectsGatewayOwnerMismatchBeforeLookingUpTheProfile() throws Exception {
        mockMvc.perform(get("/api/v1/user/8")
                        .header(OwnershipVerifier.GATEWAY_AUTHORIZATION_HEADER, GATEWAY_TOKEN)
                        .header(OwnershipVerifier.HEADER, "7"))
                .andExpect(status().isForbidden());

        verifyNoInteractions(userService);
    }
}
