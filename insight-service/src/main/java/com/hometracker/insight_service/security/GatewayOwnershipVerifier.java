package com.hometracker.insight_service.security;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/**
 * Verifies that requests to the Insight API originated at the API gateway
 * before trusting the gateway-injected owner header.
 */
@Component
public class GatewayOwnershipVerifier {

    public static final String AUTHENTICATED_USER_HEADER = "X-Authenticated-User-Id";
    public static final String GATEWAY_AUTHORIZATION_HEADER = "X-Gateway-Authorization";
    public static final String INTERNAL_SERVICE_TOKEN_HEADER = "X-Internal-Service-Token";

    private final String gatewayInternalToken;

    public GatewayOwnershipVerifier(
            @Value("${security.internal.gateway-token:}") String gatewayInternalToken) {
        this.gatewayInternalToken = gatewayInternalToken == null ? "" : gatewayInternalToken;
    }

    /**
     * Verifies gateway provenance and, when an owner was supplied by the
     * gateway, confirms that it matches the user identifier in the route.
     * Absence of the owner header represents a gateway-authorized admin route.
     */
    public void verifyGatewayOwnership(HttpServletRequest request, Long resourceUserId) {
        String gatewayProof = request.getHeader(GATEWAY_AUTHORIZATION_HEADER);
        if (!constantTimeEquals(gatewayInternalToken, gatewayProof)) {
            throw new InternalAuthenticationException(
                    "A valid API gateway authorization credential is required");
        }

        if (hasValue(request.getHeader(INTERNAL_SERVICE_TOKEN_HEADER))) {
            throw new InternalAuthenticationException(
                    "Gateway requests must not include an internal service credential");
        }

        String authenticatedUser = request.getHeader(AUTHENTICATED_USER_HEADER);
        if (!hasValue(authenticatedUser)) {
            // The API gateway omits the header for an authenticated ADMIN route.
            return;
        }

        try {
            if (!Long.valueOf(authenticatedUser).equals(resourceUserId)) {
                throw new ResourceOwnershipException(
                        "Authenticated user does not own this insight resource");
            }
        } catch (NumberFormatException exception) {
            throw new ResourceOwnershipException("Invalid authenticated-user header");
        }
    }

    private static boolean hasValue(String value) {
        return value != null && !value.isBlank();
    }

    private static boolean constantTimeEquals(String expected, String supplied) {
        return hasValue(expected) && hasValue(supplied)
                && MessageDigest.isEqual(expected.getBytes(StandardCharsets.UTF_8),
                supplied.getBytes(StandardCharsets.UTF_8));
    }
}
