package com.hometracker.user_service.security;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class OwnershipVerifierTest {
    private final OwnershipVerifier verifier = new OwnershipVerifier("gateway-proof", "internal-service-token");

    @Test
    void permitsMatchingGatewayProfileAndRejectsCrossProfileAccess() {
        MockHttpServletRequest allowed = gatewayRequest("1");
        OwnershipVerifier.CallerType caller = verifier.authenticate(allowed, false);
        assertDoesNotThrow(() -> verifier.verifyOwnershipForGateway(allowed, 1L, caller));

        MockHttpServletRequest denied = gatewayRequest("1");
        OwnershipVerifier.CallerType deniedCaller = verifier.authenticate(denied, false);
        assertThrows(ResourceOwnershipException.class,
                () -> verifier.verifyOwnershipForGateway(denied, 2L, deniedCaller));
    }

    @Test
    void permitsGatewayAdminCreationButNotProfileCreationByAUser() {
        MockHttpServletRequest adminRequest = new MockHttpServletRequest();
        adminRequest.addHeader(OwnershipVerifier.GATEWAY_AUTHORIZATION_HEADER, "gateway-proof");
        assertDoesNotThrow(() -> verifier.verifyGatewayCanCreate(adminRequest));

        MockHttpServletRequest userRequest = gatewayRequest("1");
        assertThrows(ResourceOwnershipException.class,
                () -> verifier.verifyGatewayCanCreate(userRequest));
    }

    @Test
    void rejectsBareOrForgedCallsAndAllowsAnInternalReadCaller() {
        assertThrows(InternalAuthenticationException.class,
                () -> verifier.authenticate(new MockHttpServletRequest(), true));

        MockHttpServletRequest forgedOwner = new MockHttpServletRequest();
        forgedOwner.addHeader(OwnershipVerifier.HEADER, "1");
        assertThrows(InternalAuthenticationException.class,
                () -> verifier.authenticate(forgedOwner, true));

        MockHttpServletRequest internalRead = new MockHttpServletRequest();
        internalRead.addHeader(OwnershipVerifier.INTERNAL_SERVICE_TOKEN_HEADER, "internal-service-token");
        OwnershipVerifier.CallerType caller = verifier.authenticate(internalRead, true);
        assertEquals(OwnershipVerifier.CallerType.INTERNAL_SERVICE, caller);
        assertDoesNotThrow(() -> verifier.verifyOwnershipForGateway(internalRead, 1L, caller));

        assertThrows(InternalAuthenticationException.class,
                () -> verifier.verifyGatewayCanCreate(internalRead));
    }

    private MockHttpServletRequest gatewayRequest(String ownerId) {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader(OwnershipVerifier.GATEWAY_AUTHORIZATION_HEADER, "gateway-proof");
        request.addHeader(OwnershipVerifier.HEADER, ownerId);
        return request;
    }
}
