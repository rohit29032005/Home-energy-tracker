package com.hometracker.alert_service.security;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/**
 * Verifies that alert HTTP endpoints are reached through the API gateway.
 *
 * <p>Kafka listeners are intentionally not involved in this verifier: their
 * authentication and delivery behavior is independent of the HTTP API.</p>
 */
@Component
public class AlertApiAuthorizationVerifier {
    public static final String AUTHENTICATED_USER_HEADER = "X-Authenticated-User-Id";
    public static final String GATEWAY_AUTHORIZATION_HEADER = "X-Gateway-Authorization";
    public static final String INTERNAL_SERVICE_TOKEN_HEADER = "X-Internal-Service-Token";

    private final String gatewayInternalToken;

    public AlertApiAuthorizationVerifier(
            @Value("${security.internal.gateway-token:}") String gatewayInternalToken) {
        this.gatewayInternalToken = gatewayInternalToken == null ? "" : gatewayInternalToken;
    }

    /**
     * Validates a gateway call that is restricted to an administrator. The
     * gateway omits the owner header for administrator routes.
     */
    public void verifyGatewayAdmin(HttpServletRequest request) {
        verifyGateway(request);
        if (hasValue(request.getHeader(AUTHENTICATED_USER_HEADER))) {
            throw new ResourceOwnershipException(
                    "Authenticated users cannot access an administrative alert endpoint");
        }
    }

    /**
     * Validates a gateway call for a user-scoped resource. A missing owner
     * header represents a trusted gateway administrator; a present header must
     * match the resource owner.
     */
    public void verifyUserAlertAccess(HttpServletRequest request, Long resourceUserId) {
        verifyGateway(request);
        String ownerHeader = request.getHeader(AUTHENTICATED_USER_HEADER);
        if (!hasValue(ownerHeader)) {
            return;
        }
        try {
            if (!Long.valueOf(ownerHeader).equals(resourceUserId)) {
                throw new ResourceOwnershipException(
                        "Authenticated user does not own this alert resource");
            }
        } catch (NumberFormatException exception) {
            throw new ResourceOwnershipException("Invalid authenticated-user header");
        }
    }

    private void verifyGateway(HttpServletRequest request) {
        String gatewayProof = request.getHeader(GATEWAY_AUTHORIZATION_HEADER);
        if (!constantTimeEquals(gatewayInternalToken, gatewayProof)) {
            throw new InternalAuthenticationException("A valid gateway credential is required");
        }
        if (hasValue(request.getHeader(INTERNAL_SERVICE_TOKEN_HEADER))) {
            throw new InternalAuthenticationException(
                    "Gateway requests must not include an internal service credential");
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
