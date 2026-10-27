package com.hometracker.device_service.security;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class OwnershipVerifierTest {
    private final OwnershipVerifier verifier = new OwnershipVerifier("gateway-proof", "internal-service-token");

    @Test
    void permitsMatchingGatewayOwnerAndRejectsCrossOwnerAccess() {
        MockHttpServletRequest allowed = gatewayRequest("7");
        OwnershipVerifier.CallerType caller = verifier.authenticate(allowed, false);
        assertDoesNotThrow(() -> verifier.verifyOwnershipForGateway(allowed, 7L, caller));

        MockHttpServletRequest denied = gatewayRequest("7");
        OwnershipVerifier.CallerType deniedCaller = verifier.authenticate(denied, false);
        assertThrows(ResourceOwnershipException.class,
                () -> verifier.verifyOwnershipForGateway(denied, 8L, deniedCaller));
    }

    @Test
    void rejectsBareAndForgedCallsBeforeOwnershipLookup() {
        assertThrows(InternalAuthenticationException.class,
                () -> verifier.authenticate(new MockHttpServletRequest(), true));

        MockHttpServletRequest forgedOwner = new MockHttpServletRequest();
        forgedOwner.addHeader(OwnershipVerifier.HEADER, "7");
        assertThrows(InternalAuthenticationException.class,
                () -> verifier.authenticate(forgedOwner, true));

        MockHttpServletRequest forgedGateway = new MockHttpServletRequest();
        forgedGateway.addHeader(OwnershipVerifier.GATEWAY_AUTHORIZATION_HEADER, "forged-proof");
        assertThrows(InternalAuthenticationException.class,
                () -> verifier.authenticate(forgedGateway, true));
    }

    @Test
    void permitsASeparateInternalTokenOnlyForReadCallers() {
        MockHttpServletRequest internalRead = new MockHttpServletRequest();
        internalRead.addHeader(OwnershipVerifier.INTERNAL_SERVICE_TOKEN_HEADER, "internal-service-token");
        OwnershipVerifier.CallerType caller = verifier.authenticate(internalRead, true);
        assertEquals(OwnershipVerifier.CallerType.INTERNAL_SERVICE, caller);
        assertDoesNotThrow(() -> verifier.verifyOwnershipForGateway(internalRead, 7L, caller));

        MockHttpServletRequest smuggledOwner = new MockHttpServletRequest();
        smuggledOwner.addHeader(OwnershipVerifier.INTERNAL_SERVICE_TOKEN_HEADER, "internal-service-token");
        smuggledOwner.addHeader(OwnershipVerifier.HEADER, "7");
        assertThrows(InternalAuthenticationException.class,
                () -> verifier.authenticate(smuggledOwner, true));
    }

    private MockHttpServletRequest gatewayRequest(String ownerId) {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader(OwnershipVerifier.GATEWAY_AUTHORIZATION_HEADER, "gateway-proof");
        request.addHeader(OwnershipVerifier.HEADER, ownerId);
        return request;
    }
}
