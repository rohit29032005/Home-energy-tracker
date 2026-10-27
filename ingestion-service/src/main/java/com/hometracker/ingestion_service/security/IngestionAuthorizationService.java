package com.hometracker.ingestion_service.security;

import com.hometracker.ingestion_service.dto.EnergyUsageDto;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.server.ResponseStatusException;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.HashSet;
import java.util.Set;

/**
 * Defence-in-depth authorization at the service that publishes telemetry.
 *
 * The gateway authenticates an interactive JWT or a machine token first. This
 * service then binds a JWT-originated request to the actual device owner, or a
 * machine token to the exact deviceId in its payload. Therefore neither an
 * authenticated user nor a leaked token may change only the body deviceId to
 * publish telemetry for another device.
 */
@Service
public class IngestionAuthorizationService {
    public static final String AUTHENTICATED_USER_HEADER = "X-Authenticated-User-Id";
    public static final String DEVICE_TOKEN_HEADER = "X-Device-Token";
    public static final String GATEWAY_AUTHORIZATION_HEADER = "X-Gateway-Authorization";

    private final RestTemplate restTemplate;
    private final boolean authorizationRequired;
    private final String deviceServiceUrl;
    private final Map<Long, String> deviceTokens;
    private final boolean legacyGlobalTokenEnabled;
    private final String legacyGlobalToken;
    private final String gatewayInternalToken;

    @Autowired
    public IngestionAuthorizationService(
            @Value("${ingestion.authorization.required:false}") boolean authorizationRequired,
            @Value("${device.service.url:http://localhost:8082/api/v1/device}") String deviceServiceUrl,
            @Value("${iot.ingestion.device-tokens:}") String configuredDeviceTokens,
            @Value("${iot.ingestion.allow-legacy-global-token:false}") boolean legacyGlobalTokenEnabled,
            @Value("${iot.ingestion.token:}") String legacyGlobalToken,
            @Value("${iot.ingestion.gateway-internal-token:}") String gatewayInternalToken) {
        this(new RestTemplate(), authorizationRequired, deviceServiceUrl, configuredDeviceTokens,
                legacyGlobalTokenEnabled, legacyGlobalToken, gatewayInternalToken);
    }

    IngestionAuthorizationService(RestTemplate restTemplate,
                                  boolean authorizationRequired,
                                  String deviceServiceUrl,
                                  String configuredDeviceTokens,
                                  boolean legacyGlobalTokenEnabled,
                                  String legacyGlobalToken,
                                  String gatewayInternalToken) {
        this.restTemplate = restTemplate;
        this.authorizationRequired = authorizationRequired;
        this.deviceServiceUrl = stripTrailingSlash(deviceServiceUrl);
        this.deviceTokens = parseDeviceTokens(configuredDeviceTokens);
        this.legacyGlobalTokenEnabled = legacyGlobalTokenEnabled;
        this.legacyGlobalToken = legacyGlobalToken == null ? "" : legacyGlobalToken;
        this.gatewayInternalToken = gatewayInternalToken == null ? "" : gatewayInternalToken;
        if (authorizationRequired && this.deviceTokens.isEmpty()
                && (!legacyGlobalTokenEnabled || this.legacyGlobalToken.isBlank())) {
            throw new IllegalStateException(
                    "Telemetry authorization is enabled but no device-bound token mapping is configured");
        }
        if (authorizationRequired && this.gatewayInternalToken.isBlank()) {
            throw new IllegalStateException(
                    "Telemetry authorization is enabled but no gateway-to-ingestion proof is configured");
        }
    }

    public void authorize(EnergyUsageDto telemetry, HttpServletRequest request) {
        if (!authorizationRequired) {
            return;
        }
        String authenticatedUserId = request.getHeader(AUTHENTICATED_USER_HEADER);
        if (authenticatedUserId != null && !authenticatedUserId.isBlank()) {
            if (!constantTimeEquals(gatewayInternalToken,
                    request.getHeader(GATEWAY_AUTHORIZATION_HEADER))) {
                throw new ResponseStatusException(HttpStatus.UNAUTHORIZED,
                        "Gateway-authenticated telemetry proof is required");
            }
            verifyOwner(telemetry.deviceId(), authenticatedUserId);
            return;
        }
        String deviceToken = request.getHeader(DEVICE_TOKEN_HEADER);
        if (deviceTokenMatches(telemetry.deviceId(), deviceToken)) {
            return;
        }
        throw new ResponseStatusException(HttpStatus.UNAUTHORIZED,
                "A device-bound telemetry credential is required for this device");
    }

    private void verifyOwner(Long deviceId, String authenticatedUserId) {
        try {
            Long.parseLong(authenticatedUserId);
        } catch (NumberFormatException exception) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN,
                    "The authenticated user identity is invalid", exception);
        }
        HttpHeaders headers = new HttpHeaders();
        headers.set(AUTHENTICATED_USER_HEADER, authenticatedUserId);
        headers.set(GATEWAY_AUTHORIZATION_HEADER, gatewayInternalToken);
        try {
            ResponseEntity<Void> response = restTemplate.exchange(
                    deviceServiceUrl + "/" + deviceId,
                    HttpMethod.GET,
                    new HttpEntity<>(headers),
                    Void.class);
            if (!response.getStatusCode().is2xxSuccessful()) {
                throw forbiddenOwnership();
            }
        } catch (ResponseStatusException exception) {
            throw exception;
        } catch (RestClientException exception) {
            // Any non-2xx response, including a missing device, fails closed.
            throw forbiddenOwnership();
        }
    }

    private boolean deviceTokenMatches(Long deviceId, String suppliedToken) {
        if (suppliedToken == null || suppliedToken.isBlank()) {
            return false;
        }
        String configuredToken = deviceTokens.get(deviceId);
        if (configuredToken != null && constantTimeEquals(configuredToken, suppliedToken)) {
            return true;
        }
        return legacyGlobalTokenEnabled && constantTimeEquals(legacyGlobalToken, suppliedToken);
    }

    private ResponseStatusException forbiddenOwnership() {
        return new ResponseStatusException(HttpStatus.FORBIDDEN,
                "The authenticated user does not own the telemetry device");
    }

    private static Map<Long, String> parseDeviceTokens(String configuredDeviceTokens) {
        Map<Long, String> tokens = new LinkedHashMap<>();
        Set<String> tokenValues = new HashSet<>();
        if (configuredDeviceTokens == null || configuredDeviceTokens.isBlank()) {
            return Map.of();
        }
        for (String rawEntry : configuredDeviceTokens.split(",")) {
            String entry = rawEntry.trim();
            String[] parts = entry.split(":", 2);
            if (parts.length != 2 || parts[0].isBlank() || parts[1].isBlank()) {
                throw new IllegalArgumentException(
                        "iot.ingestion.device-tokens entries must use deviceId:token format");
            }
            Long deviceId;
            try {
                deviceId = Long.parseLong(parts[0].trim());
            } catch (NumberFormatException exception) {
                throw new IllegalArgumentException("Device token mapping contains an invalid device ID", exception);
            }
            String token = parts[1].trim();
            if (deviceId < 1 || tokens.putIfAbsent(deviceId, token) != null) {
                throw new IllegalArgumentException("Device token mapping contains a duplicate or invalid device ID");
            }
            if (!tokenValues.add(token)) {
                throw new IllegalArgumentException(
                        "Device token mapping must not reuse a token across multiple devices");
            }
        }
        return Map.copyOf(tokens);
    }

    private static boolean constantTimeEquals(String expected, String supplied) {
        if (expected == null || expected.isBlank() || supplied == null || supplied.isBlank()) {
            return false;
        }
        return MessageDigest.isEqual(expected.getBytes(StandardCharsets.UTF_8),
                supplied.getBytes(StandardCharsets.UTF_8));
    }

    private static String stripTrailingSlash(String url) {
        return url.endsWith("/") ? url.substring(0, url.length() - 1) : url;
    }
}
