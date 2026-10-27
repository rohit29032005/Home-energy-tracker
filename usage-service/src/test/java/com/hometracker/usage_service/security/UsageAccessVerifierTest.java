package com.hometracker.usage_service.security;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class UsageAccessVerifierTest {
    private final UsageAccessVerifier verifier =
            new UsageAccessVerifier("gateway-proof", "internal-service-token");

    @Test
    void permitsMatchingGatewayOwnerAndRejectsAnotherUsersUsage() {
        MockHttpServletRequest allowed = gatewayRequest("7");
        UsageAccessVerifier.CallerType caller = verifier.authenticate(allowed, true);
        assertDoesNotThrow(() -> verifier.verifyUsageAccess(allowed, 7L, caller));

        MockHttpServletRequest denied = gatewayRequest("7");
        UsageAccessVerifier.CallerType deniedCaller = verifier.authenticate(denied, true);
        assertThrows(ResourceOwnershipException.class,
                () -> verifier.verifyUsageAccess(denied, 8L, deniedCaller));
    }

    @Test
    void preservesGatewayAdministratorSemanticsWhenTheOwnerHeaderIsAbsent() {
        MockHttpServletRequest administratorRequest = new MockHttpServletRequest();
        administratorRequest.addHeader(
                UsageAccessVerifier.GATEWAY_AUTHORIZATION_HEADER, "gateway-proof");

        UsageAccessVerifier.CallerType caller = verifier.authenticate(administratorRequest, true);

        assertDoesNotThrow(() -> verifier.verifyUsageAccess(administratorRequest, 7L, caller));
    }

    @Test
    void rejectsMissingForgedAndMixedCredentials() {
        assertThrows(InternalAuthenticationException.class,
                () -> verifier.authenticate(new MockHttpServletRequest(), true));

        MockHttpServletRequest forgedGateway = new MockHttpServletRequest();
        forgedGateway.addHeader(
                UsageAccessVerifier.GATEWAY_AUTHORIZATION_HEADER, "forged-gateway-proof");
        assertThrows(InternalAuthenticationException.class,
                () -> verifier.authenticate(forgedGateway, true));

        MockHttpServletRequest mixedCredentials = gatewayRequest("7");
        mixedCredentials.addHeader(
                UsageAccessVerifier.INTERNAL_SERVICE_TOKEN_HEADER, "internal-service-token");
        assertThrows(InternalAuthenticationException.class,
                () -> verifier.authenticate(mixedCredentials, true));
    }

    @Test
    void permitsOnlyAHeaderCleanInternalReadCaller() {
        MockHttpServletRequest internalRead = new MockHttpServletRequest();
        internalRead.addHeader(
                UsageAccessVerifier.INTERNAL_SERVICE_TOKEN_HEADER, "internal-service-token");
        UsageAccessVerifier.CallerType caller = verifier.authenticate(internalRead, true);

        assertEquals(UsageAccessVerifier.CallerType.INTERNAL_SERVICE, caller);
        assertDoesNotThrow(() -> verifier.verifyUsageAccess(internalRead, 7L, caller));

        MockHttpServletRequest smuggledOwner = new MockHttpServletRequest();
        smuggledOwner.addHeader(
                UsageAccessVerifier.INTERNAL_SERVICE_TOKEN_HEADER, "internal-service-token");
        smuggledOwner.addHeader(UsageAccessVerifier.AUTHENTICATED_USER_HEADER, "7");
        assertThrows(InternalAuthenticationException.class,
                () -> verifier.authenticate(smuggledOwner, true));
    }

    private static MockHttpServletRequest gatewayRequest(String ownerId) {
        MockHttpServletRequest request = new MockHttpServletRequest();
        request.addHeader(UsageAccessVerifier.GATEWAY_AUTHORIZATION_HEADER, "gateway-proof");
        request.addHeader(UsageAccessVerifier.AUTHENTICATED_USER_HEADER, ownerId);
        return request;
    }
}
