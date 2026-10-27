package com.hometracker.api_gateway.filter;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.Collection;
import java.util.Set;
import java.util.Map;
import java.util.Optional;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Enforces user-id path ownership at the public boundary and forwards a trusted
 * owner header to Device/User services for resource-id checks. Docker hides the
 * downstream service ports so this header cannot be supplied from the host.
 */
@Component
public class OwnershipGatewayFilter implements GlobalFilter, Ordered {
    public static final String AUTHENTICATED_USER_HEADER = "X-Authenticated-User-Id";
    public static final String GATEWAY_AUTHORIZATION_HEADER = "X-Gateway-Authorization";
    public static final String INTERNAL_SERVICE_TOKEN_HEADER = "X-Internal-Service-Token";
    private static final Set<String> ADMIN_ONLY_PATHS = Set.of(
            "/api/v1/user",
            "/api/v1/alert",
            "/api/v1/alert/test-send"
    );
    private static final Pattern USER_ID_PATH = Pattern.compile(
            "^/api/v1/(?:user|usage|device/user|alert/user)/(\\d+)(?:/.*)?$");
    private static final Pattern INSIGHT_USER_ID_PATH = Pattern.compile(
            "^/api/v1/insight/(?:saving-tips|overview|bill-forecast|appliance-ranking|standby-detective)/(\\d+)(?:/.*)?$");

    private final boolean securityEnabled;
    private final String gatewayInternalToken;

    @Autowired
    public OwnershipGatewayFilter(@Value("${security.enabled:false}") boolean securityEnabled,
                                  @Value("${iot.ingestion.gateway-internal-token:}") String gatewayInternalToken) {
        this.securityEnabled = securityEnabled;
        this.gatewayInternalToken = gatewayInternalToken == null ? "" : gatewayInternalToken;
    }

    /** Test-friendly constructor for configurations without the internal token. */
    public OwnershipGatewayFilter(boolean securityEnabled) {
        this(securityEnabled, "");
    }

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        String path = exchange.getRequest().getPath().value();
        if (!securityEnabled || !path.startsWith("/api/v1/") || "/api/v1/ingestion".equals(path)) {
            return chain.filter(exchange);
        }
        // Resolve a missing principal before invoking the downstream chain.
        // GatewayFilterChain returns Mono<Void>; a successful proxied response
        // also completes empty, so a trailing switchIfEmpty would otherwise
        // deny valid requests after the response body has been written.
        return exchange.getPrincipal()
                .map(Optional::of)
                .defaultIfEmpty(Optional.empty())
                .flatMap(optionalPrincipal -> {
            if (optionalPrincipal.isEmpty()
                    || !(optionalPrincipal.get() instanceof JwtAuthenticationToken authentication)) {
                return deny(exchange);
            }
            boolean administrator = hasAdminRole(authentication.getToken().getClaim("realm_access"));
            Long authenticatedUserId = claimAsLong(authentication.getToken().getClaim("home_energy_user_id"));
            if (!administrator && authenticatedUserId == null) {
                return deny(exchange);
            }
            // Collection-wide profile/alert data and direct test-email
            // dispatch are administrative resources. A regular user may
            // retrieve only data addressed to its ownership claim.
            if (!administrator && ADMIN_ONLY_PATHS.contains(path)) {
                return deny(exchange);
            }
            Long requestedUserId = requestedUserId(exchange.getRequest().getPath().value());
            if (!administrator && requestedUserId != null && !authenticatedUserId.equals(requestedUserId)) {
                return deny(exchange);
            }
            if (gatewayInternalToken.isBlank()) {
                // Do not send authenticated requests to services that are
                // configured to require a gateway caller credential.
                return deny(exchange);
            }
            ServerHttpRequest trustedRequest = exchange.getRequest().mutate()
                    .headers(headers -> {
                        headers.remove(AUTHENTICATED_USER_HEADER);
                        headers.remove(GATEWAY_AUTHORIZATION_HEADER);
                        headers.remove(INTERNAL_SERVICE_TOKEN_HEADER);
                        if (!administrator) {
                            headers.add(AUTHENTICATED_USER_HEADER, authenticatedUserId.toString());
                        }
                        headers.add(GATEWAY_AUTHORIZATION_HEADER, gatewayInternalToken);
                    })
                    .build();
            return chain.filter(exchange.mutate().request(trustedRequest).build());
        });
    }

    private Mono<Void> deny(ServerWebExchange exchange) {
        exchange.getResponse().setStatusCode(HttpStatus.FORBIDDEN);
        return exchange.getResponse().setComplete();
    }

    private Long requestedUserId(String path) {
        for (Pattern pattern : new Pattern[]{USER_ID_PATH, INSIGHT_USER_ID_PATH}) {
            Matcher matcher = pattern.matcher(path);
            if (matcher.matches()) {
                return Long.parseLong(matcher.group(1));
            }
        }
        return null;
    }

    @SuppressWarnings("unchecked")
    private boolean hasAdminRole(Object realmAccess) {
        if (!(realmAccess instanceof Map<?, ?> access) || !(access.get("roles") instanceof Collection<?> roles)) {
            return false;
        }
        return roles.stream().map(String::valueOf).anyMatch("ADMIN"::equals);
    }

    private Long claimAsLong(Object value) {
        try {
            return value == null ? null : Long.valueOf(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    @Override
    public int getOrder() {
        return Ordered.HIGHEST_PRECEDENCE + 20;
    }
}
