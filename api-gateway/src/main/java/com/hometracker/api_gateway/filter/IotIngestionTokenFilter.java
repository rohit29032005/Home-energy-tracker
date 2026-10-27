package com.hometracker.api_gateway.filter;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.Optional;
import java.util.Set;
import java.util.stream.Collectors;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

/**
 * Accepts the Wokwi telemetry route only from an authenticated user JWT or the
 * configured machine token. It avoids granting unauthenticated write access
 * merely to keep simulator compatibility.
 */
@Component
public class IotIngestionTokenFilter implements GlobalFilter, Ordered {
    public static final String AUTHENTICATED_USER_HEADER = "X-Authenticated-User-Id";
    public static final String GATEWAY_AUTHORIZATION_HEADER = "X-Gateway-Authorization";
    public static final String INTERNAL_SERVICE_TOKEN_HEADER = "X-Internal-Service-Token";
    private final boolean securityEnabled;
    private final String ingestionToken;
    private final Set<String> configuredDeviceTokens;
    private final String gatewayInternalToken;

    @Autowired
    public IotIngestionTokenFilter(@Value("${security.enabled:false}") boolean securityEnabled,
                                   @Value("${iot.ingestion.token:}") String ingestionToken,
                                   @Value("${iot.ingestion.device-tokens:}") String configuredDeviceTokens,
                                   @Value("${iot.ingestion.gateway-internal-token:}") String gatewayInternalToken) {
        this.securityEnabled = securityEnabled;
        this.ingestionToken = ingestionToken;
        this.configuredDeviceTokens = parseConfiguredTokens(configuredDeviceTokens);
        this.gatewayInternalToken = gatewayInternalToken == null ? "" : gatewayInternalToken;
    }

    /** Test-friendly constructor that retains the legacy single-token contract. */
    public IotIngestionTokenFilter(boolean securityEnabled, String ingestionToken) {
        this(securityEnabled, ingestionToken, "", "");
    }

    /** Test-friendly constructor for an explicit device-token mapping. */
    public IotIngestionTokenFilter(boolean securityEnabled,
                                   String ingestionToken,
                                   String configuredDeviceTokens) {
        this(securityEnabled, ingestionToken, configuredDeviceTokens, "");
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        boolean telemetryRequest = exchange.getRequest().getMethod() == HttpMethod.POST
                && "/api/v1/ingestion".equals(exchange.getRequest().getPath().value());
        if (!securityEnabled || !telemetryRequest) {
            return chain.filter(exchange);
        }
        String providedToken = exchange.getRequest().getHeaders().getFirst("X-Device-Token");
        if (isConfiguredMachineToken(providedToken)) {
            // A caller must never be able to smuggle a user identity alongside
            // a machine credential. The downstream service decides the device
            // binding using the device token and the body deviceId.
            ServerHttpRequest machineRequest = exchange.getRequest().mutate()
                    .headers(headers -> {
                        headers.remove(AUTHENTICATED_USER_HEADER);
                        headers.remove(GATEWAY_AUTHORIZATION_HEADER);
                        headers.remove(INTERNAL_SERVICE_TOKEN_HEADER);
                    })
                    .build();
            return chain.filter(exchange.mutate().request(machineRequest).build());
        }
        // Resolve an authenticated principal before invoking the downstream
        // chain. A successful GatewayFilterChain is a Mono<Void>, so using a
        // trailing switchIfEmpty after chain.filter(...) would misclassify a
        // normal completion as an absent principal.
        return exchange.getPrincipal()
                .map(principal -> principal instanceof JwtAuthenticationToken token
                        ? Optional.ofNullable(claimAsLong(token))
                        : Optional.<Long>empty())
                .defaultIfEmpty(Optional.empty())
                .flatMap(authenticatedUserId -> {
                    if (authenticatedUserId.isEmpty()) {
                        return reject(exchange);
                    }
                    if (gatewayInternalToken.isBlank()) {
                        // Do not forward a trusted owner header when the
                        // gateway-to-ingestion proof was not configured.
                        return reject(exchange);
                    }
                    ServerHttpRequest userRequest = exchange.getRequest().mutate()
                            .headers(headers -> {
                                headers.remove(AUTHENTICATED_USER_HEADER);
                                headers.remove(GATEWAY_AUTHORIZATION_HEADER);
                                headers.remove(INTERNAL_SERVICE_TOKEN_HEADER);
                                headers.add(AUTHENTICATED_USER_HEADER, authenticatedUserId.get().toString());
                                headers.add(GATEWAY_AUTHORIZATION_HEADER, gatewayInternalToken);
                            })
                            .build();
                    return chain.filter(exchange.mutate().request(userRequest).build());
                });
    }

    private Long claimAsLong(JwtAuthenticationToken token) {
        Object value = token.getToken().getClaim("home_energy_user_id");
        try {
            return value == null ? null : Long.valueOf(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private boolean isConfiguredMachineToken(String providedToken) {
        if (providedToken == null || providedToken.isBlank()) {
            return false;
        }
        if (constantTimeEquals(ingestionToken, providedToken)) {
            return true;
        }
        return configuredDeviceTokens.stream().anyMatch(token -> constantTimeEquals(token, providedToken));
    }

    private static Set<String> parseConfiguredTokens(String mappings) {
        if (mappings == null || mappings.isBlank()) {
            return Set.of();
        }
        return java.util.Arrays.stream(mappings.split(","))
                .map(String::trim)
                .map(entry -> entry.split(":", 2))
                .filter(parts -> parts.length == 2 && !parts[0].isBlank() && !parts[1].isBlank())
                .map(parts -> parts[1].trim())
                .collect(Collectors.toUnmodifiableSet());
    }

    private static boolean constantTimeEquals(String expected, String provided) {
        return expected != null && !expected.isBlank()
                && MessageDigest.isEqual(expected.getBytes(StandardCharsets.UTF_8),
                provided.getBytes(StandardCharsets.UTF_8));
    }

    private Mono<Void> reject(ServerWebExchange exchange) {
        exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
        return exchange.getResponse().setComplete();
    }

    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE + 10;
    }
}
