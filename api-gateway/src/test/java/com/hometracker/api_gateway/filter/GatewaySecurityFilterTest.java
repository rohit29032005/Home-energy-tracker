package com.hometracker.api_gateway.filter;

import org.junit.jupiter.api.Test;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.http.HttpStatus;
import org.springframework.mock.http.server.reactive.MockServerHttpRequest;
import org.springframework.mock.web.server.MockServerWebExchange;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.web.server.ServerWebExchange;
import org.springframework.web.server.ServerWebExchangeDecorator;
import reactor.core.publisher.Mono;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicReference;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class GatewaySecurityFilterTest {

    @Test
    void rejectsUnauthenticatedTelemetryWithoutMachineToken() {
        IotIngestionTokenFilter filter = new IotIngestionTokenFilter(true, "machine-token");
        MockServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.post("/api/v1/ingestion").build());

        filter.filter(exchange, passedChain()).block();

        assertEquals(HttpStatus.UNAUTHORIZED, exchange.getResponse().getStatusCode());
    }

    @Test
    void acceptsTelemetryWithConfiguredMachineToken() {
        IotIngestionTokenFilter filter = new IotIngestionTokenFilter(true, "machine-token");
        MockServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.post("/api/v1/ingestion")
                        .header("X-Device-Token", "machine-token")
                        .header(IotIngestionTokenFilter.AUTHENTICATED_USER_HEADER, "spoofed-user")
                        .header(IotIngestionTokenFilter.GATEWAY_AUTHORIZATION_HEADER, "forged-proof")
                        .header(IotIngestionTokenFilter.INTERNAL_SERVICE_TOKEN_HEADER, "forged-service-token")
                        .build());
        AtomicReference<ServerWebExchange> forwarded = new AtomicReference<>();

        filter.filter(exchange, captureChain(forwarded)).block();

        assertNull(exchange.getResponse().getStatusCode());
        assertTrue(forwarded.get() != null);
        assertNull(forwarded.get().getRequest().getHeaders()
                .getFirst(IotIngestionTokenFilter.AUTHENTICATED_USER_HEADER));
        assertNull(forwarded.get().getRequest().getHeaders()
                .getFirst(IotIngestionTokenFilter.GATEWAY_AUTHORIZATION_HEADER));
        assertNull(forwarded.get().getRequest().getHeaders()
                .getFirst(IotIngestionTokenFilter.INTERNAL_SERVICE_TOKEN_HEADER));
    }

    @Test
    void acceptsAConfiguredDeviceTokenAtTheGatewayButStripsSpoofedOwnerHeader() {
        IotIngestionTokenFilter filter = new IotIngestionTokenFilter(
                true, "legacy-token", "1:device-one-token,2:device-two-token");
        MockServerWebExchange exchange = MockServerWebExchange.from(
                MockServerHttpRequest.post("/api/v1/ingestion")
                        .header("X-Device-Token", "device-two-token")
                        .header(IotIngestionTokenFilter.AUTHENTICATED_USER_HEADER, "spoofed-user")
                        .header(IotIngestionTokenFilter.GATEWAY_AUTHORIZATION_HEADER, "forged-proof").build());
        AtomicReference<ServerWebExchange> forwarded = new AtomicReference<>();

        filter.filter(exchange, captureChain(forwarded)).block();

        assertNull(exchange.getResponse().getStatusCode());
        assertTrue(forwarded.get() != null);
        assertNull(forwarded.get().getRequest().getHeaders()
                .getFirst(IotIngestionTokenFilter.AUTHENTICATED_USER_HEADER));
        assertNull(forwarded.get().getRequest().getHeaders()
                .getFirst(IotIngestionTokenFilter.GATEWAY_AUTHORIZATION_HEADER));
    }

    @Test
    void acceptsTelemetryWithAuthenticatedJwtWithoutReplacingTheResponse() {
        IotIngestionTokenFilter filter = new IotIngestionTokenFilter(
                true, "machine-token", "", "gateway-proof");
        AtomicReference<ServerWebExchange> forwarded = new AtomicReference<>();
        ServerWebExchange exchange = authenticatedExchange(
                MockServerHttpRequest.post("/api/v1/ingestion")
                        .header(IotIngestionTokenFilter.AUTHENTICATED_USER_HEADER, "spoofed-user")
                        .header(IotIngestionTokenFilter.GATEWAY_AUTHORIZATION_HEADER, "forged-proof")
                        .header(IotIngestionTokenFilter.INTERNAL_SERVICE_TOKEN_HEADER, "forged-service-token")
                        .build(), jwtForUser(1L));

        filter.filter(exchange, captureChain(forwarded)).block();

        assertNull(exchange.getResponse().getStatusCode());
        assertTrue(forwarded.get() != null);
        assertEquals("1", forwarded.get().getRequest().getHeaders()
                .getFirst(IotIngestionTokenFilter.AUTHENTICATED_USER_HEADER));
        assertEquals("gateway-proof", forwarded.get().getRequest().getHeaders()
                .getFirst(IotIngestionTokenFilter.GATEWAY_AUTHORIZATION_HEADER));
        assertNull(forwarded.get().getRequest().getHeaders()
                .getFirst(IotIngestionTokenFilter.INTERNAL_SERVICE_TOKEN_HEADER));
    }

    @Test
    void rejectsJwtTelemetryWhenTheGatewayProofIsNotConfigured() {
        IotIngestionTokenFilter filter = new IotIngestionTokenFilter(true, "machine-token");
        AtomicReference<ServerWebExchange> forwarded = new AtomicReference<>();
        ServerWebExchange exchange = authenticatedExchange(
                MockServerHttpRequest.post("/api/v1/ingestion").build(), jwtForUser(1L));

        filter.filter(exchange, captureChain(forwarded)).block();

        assertEquals(HttpStatus.UNAUTHORIZED, exchange.getResponse().getStatusCode());
        assertNull(forwarded.get());
    }

    @Test
    void rejectsCrossUserAndNonAdminAdministrativePathsThenForwardsTrustedOwner() {
        OwnershipGatewayFilter filter = new OwnershipGatewayFilter(true, "gateway-proof");
        JwtAuthenticationToken userOne = jwtForUser(1L);

        ServerWebExchange crossUser = authenticatedExchange("/api/v1/device/user/2", userOne);
        filter.filter(crossUser, passedChain()).block();
        assertEquals(HttpStatus.FORBIDDEN, crossUser.getResponse().getStatusCode());

        for (String administrativePath : List.of("/api/v1/user", "/api/v1/alert", "/api/v1/alert/test-send")) {
            ServerWebExchange administrativeRequest = authenticatedExchange(administrativePath, userOne);
            filter.filter(administrativeRequest, passedChain()).block();
            assertEquals(HttpStatus.FORBIDDEN, administrativeRequest.getResponse().getStatusCode());
        }

        AtomicReference<ServerWebExchange> forwarded = new AtomicReference<>();
        ServerWebExchange ownPath = authenticatedExchange("/api/v1/device/user/1", userOne);
        filter.filter(ownPath, captureChain(forwarded)).block();
        assertEquals("1", forwarded.get().getRequest().getHeaders()
                .getFirst(OwnershipGatewayFilter.AUTHENTICATED_USER_HEADER));
        assertEquals("gateway-proof", forwarded.get().getRequest().getHeaders()
                .getFirst(OwnershipGatewayFilter.GATEWAY_AUTHORIZATION_HEADER));
        assertNull(ownPath.getResponse().getStatusCode());
    }

    @Test
    void rejectsAuthenticatedApiRequestsWhenTheGatewayProofIsNotConfigured() {
        OwnershipGatewayFilter filter = new OwnershipGatewayFilter(true);
        AtomicReference<ServerWebExchange> forwarded = new AtomicReference<>();
        ServerWebExchange exchange = authenticatedExchange("/api/v1/user/1", jwtForUser(1L));

        filter.filter(exchange, captureChain(forwarded)).block();

        assertEquals(HttpStatus.FORBIDDEN, exchange.getResponse().getStatusCode());
        assertNull(forwarded.get());
    }

    @Test
    void forwardsAdministrativeCollectionAndTestPathsOnlyForAnAdministrator() {
        OwnershipGatewayFilter filter = new OwnershipGatewayFilter(true, "gateway-proof");
        for (String administrativePath : List.of("/api/v1/user", "/api/v1/alert", "/api/v1/alert/test-send")) {
            AtomicReference<ServerWebExchange> forwarded = new AtomicReference<>();
            ServerWebExchange exchange = authenticatedExchange(administrativePath, jwtForAdmin());

            filter.filter(exchange, captureChain(forwarded)).block();

            assertTrue(forwarded.get() != null);
            assertNull(forwarded.get().getRequest().getHeaders()
                    .getFirst(OwnershipGatewayFilter.AUTHENTICATED_USER_HEADER));
            assertEquals("gateway-proof", forwarded.get().getRequest().getHeaders()
                    .getFirst(OwnershipGatewayFilter.GATEWAY_AUTHORIZATION_HEADER));
            assertNull(exchange.getResponse().getStatusCode());
        }
    }

    private GatewayFilterChain passedChain() {
        return exchange -> Mono.empty();
    }

    private GatewayFilterChain captureChain(AtomicReference<ServerWebExchange> forwarded) {
        return exchange -> {
            forwarded.set(exchange);
            return Mono.empty();
        };
    }

    private ServerWebExchange authenticatedExchange(String path, JwtAuthenticationToken token) {
        return authenticatedExchange(MockServerHttpRequest.get(path).build(), token);
    }

    private ServerWebExchange authenticatedExchange(MockServerHttpRequest request, JwtAuthenticationToken token) {
        MockServerWebExchange delegate = MockServerWebExchange.from(request);
        return new ServerWebExchangeDecorator(delegate) {
            @Override
            public Mono<java.security.Principal> getPrincipal() {
                return Mono.just(token);
            }
        };
    }

    private JwtAuthenticationToken jwtForUser(long userId) {
        Jwt jwt = new Jwt("test-token", Instant.now(), Instant.now().plusSeconds(300),
                Map.of("alg", "none"), Map.of(
                "home_energy_user_id", userId,
                "realm_access", Map.of("roles", List.of("USER"))));
        return new JwtAuthenticationToken(jwt, List.of(new SimpleGrantedAuthority("ROLE_USER")));
    }

    private JwtAuthenticationToken jwtForAdmin() {
        Jwt jwt = new Jwt("admin-test-token", Instant.now(), Instant.now().plusSeconds(300),
                Map.of("alg", "none"), Map.of(
                "realm_access", Map.of("roles", List.of("ADMIN"))));
        return new JwtAuthenticationToken(jwt, List.of(new SimpleGrantedAuthority("ROLE_ADMIN")));
    }
}
