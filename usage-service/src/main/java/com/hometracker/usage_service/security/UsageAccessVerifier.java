package com.hometracker.usage_service.security;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/**
 * Authenticates callers of private usage endpoints before any usage lookup is
 * performed. Requests from the API gateway carry a gateway proof and may carry
 * the authenticated owner identifier. Background insight processing carries a
 * separate internal-service credential and cannot supply either gateway header.
 */
@Component
public class UsageAccessVerifier {
    public static final String AUTHENTICATED_USER_HEADER = "X-Authenticated-User-Id";
    public static final String GATEWAY_AUTHORIZATION_HEADER = "X-Gateway-Authorization";
    public static final String INTERNAL_SERVICE_TOKEN_HEADER = "X-Internal-Service-Token";

    public enum CallerType {
        GATEWAY,
        INTERNAL_SERVICE
    }

    private final String gatewayInternalToken;
    private final String internalServiceToken;

    @Autowired
    public UsageAccessVerifier(
            @Value("${security.internal.gateway-token:}") String gatewayInternalToken,
            @Value("${security.internal.service-token:}") String internalServiceToken) {
        this.gatewayInternalToken = gatewayInternalToken == null ? "" : gatewayInternalToken;
        this.internalServiceToken = internalServiceToken == null ? "" : internalServiceToken;
    }

    /**
     * Authenticates the immediate trusted caller. Internal-service access is
     * limited to read paths by the controller's {@code allowInternalService}
     * argument.
     */
    public CallerType authenticate(HttpServletRequest request, boolean allowInternalService) {
        String gatewayProof = request.getHeader(GATEWAY_AUTHORIZATION_HEADER);
        if (constantTimeEquals(gatewayInternalToken, gatewayProof)) {
            if (hasValue(request.getHeader(INTERNAL_SERVICE_TOKEN_HEADER))) {
                throw new InternalAuthenticationException(
                        "Gateway requests must not include an internal service credential");
            }
            return CallerType.GATEWAY;
        }

        String serviceToken = request.getHeader(INTERNAL_SERVICE_TOKEN_HEADER);
        if (allowInternalService
                && constantTimeEquals(internalServiceToken, serviceToken)
                && !hasValue(request.getHeader(AUTHENTICATED_USER_HEADER))
                && !hasValue(gatewayProof)) {
            return CallerType.INTERNAL_SERVICE;
        }

        throw new InternalAuthenticationException("A valid private-service credential is required");
    }

    /**
     * Enforces owner access for gateway traffic. The API gateway intentionally
     * omits the owner header for an authenticated administrator route; that
     * preserves the existing administrator access semantics. A trusted internal
     * insight caller is permitted only because this endpoint is read-only.
     */
    public void verifyUsageAccess(
            HttpServletRequest request, Long requestedUserId, CallerType callerType) {
        if (callerType == CallerType.INTERNAL_SERVICE) {
            return;
        }

        String ownerValue = request.getHeader(AUTHENTICATED_USER_HEADER);
        if (!hasValue(ownerValue)) {
            return;
        }

        try {
            if (!Long.valueOf(ownerValue).equals(requestedUserId)) {
                throw new ResourceOwnershipException(
                        "Authenticated user does not own this usage resource");
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
                && MessageDigest.isEqual(
                expected.getBytes(StandardCharsets.UTF_8),
                supplied.getBytes(StandardCharsets.UTF_8));
    }
}
