package com.hometracker.insight_service.client;

import com.hometracker.insight_service.dto.UsageDto;
import com.hometracker.insight_service.security.GatewayOwnershipVerifier;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.UriComponentsBuilder;

@Component
public class UsageClient {

    private final RestTemplate restTemplate;

    private final String baseUrl;
    private final String internalServiceToken;

    @Autowired
    public UsageClient(@Value("${usage.service.url}") String baseUrl,
                       @Value("${internal.service.token:}") String internalServiceToken) {
        this(new RestTemplate(), baseUrl, internalServiceToken);
    }

    UsageClient(RestTemplate restTemplate, String baseUrl, String internalServiceToken) {
        this.restTemplate = restTemplate;
        this.baseUrl = baseUrl;
        this.internalServiceToken = internalServiceToken == null ? "" : internalServiceToken;
    }

    public UsageDto getXDaysUsageForUser (Long userId, int days) {
        String url = UriComponentsBuilder
                .fromUriString(baseUrl)
                .path("/{userId}")
                .queryParam("days", days)
                .buildAndExpand(userId)
                .toUriString();

        ResponseEntity<UsageDto> response = restTemplate.exchange(
                url, HttpMethod.GET, internalRequest(), UsageDto.class);
        return response.getBody();
    }

    private HttpEntity<Void> internalRequest() {
        HttpHeaders headers = new HttpHeaders();
        if (!internalServiceToken.isBlank()) {
            headers.set(GatewayOwnershipVerifier.INTERNAL_SERVICE_TOKEN_HEADER, internalServiceToken);
        }
        return new HttpEntity<>(headers);
    }
}
