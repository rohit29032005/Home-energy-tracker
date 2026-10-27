package com.hometracker.device_service.security;

import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/**
 * Authenticates private-service callers before applying resource ownership
 * checks. Gateway-originated traffic carries a gateway proof; background
 * services carry a separate service token and may access read-only endpoints.
 */
@Component
public class OwnershipVerifier {
    public static final String HEADER = "X-Authenticated-User-Id";
    public static final String GATEWAY_AUTHORIZATION_HEADER = "X-Gateway-Authorization";
    public static final String INTERNAL_SERVICE_TOKEN_HEADER = "X-Internal-Service-Token";

    public enum CallerType {
        GATEWAY,
        INTERNAL_SERVICE
    }

    private final String gatewayInternalToken;
    private final String internalServiceToken;

    @Autowired
    public OwnershipVerifier(@Value("${security.internal.gateway-token:}") String gatewayInternalToken,
                             @Value("${security.internal.service-token:}") String internalServiceToken) {
        this.gatewayInternalToken = gatewayInternalToken == null ? "" : gatewayInternalToken;
        this.internalServiceToken = internalServiceToken == null ? "" : internalServiceToken;
    }

    /** Test-friendly constructor for an unconfigured standalone service. */
    public OwnershipVerifier() {
        this("", "");
    }

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
        if (allowInternalService && constantTimeEquals(internalServiceToken, serviceToken)
                && !hasValue(request.getHeader(HEADER)) && !hasValue(gatewayProof)) {
            return CallerType.INTERNAL_SERVICE;
        }
        throw new InternalAuthenticationException("A valid private-service credential is required");
    }

    public void verifyOwnershipForGateway(HttpServletRequest request, Long resourceUserId, CallerType callerType) {
        if (callerType == CallerType.INTERNAL_SERVICE) {
            return;
        }
        String value = request.getHeader(HEADER);
        if (value == null || value.isBlank()) {
            // The gateway omits this header for an authenticated ADMIN route.
            return;
        }
        try {
            if (!Long.valueOf(value).equals(resourceUserId)) {
                throw new ResourceOwnershipException("Authenticated user does not own this device resource");
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
