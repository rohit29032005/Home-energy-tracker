package com.hometracker.usage_service.client;

import com.hometracker.usage_service.dto.UserDto;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.UriComponentsBuilder;

@Component
public class UserClient {

    private final RestTemplate restTemplate;

    private final String baseUrl;
    private final String internalServiceToken;

    @Autowired
    public UserClient(@Value("${user.service.url}") String baseUrl,
                      @Value("${internal.service.token:}") String internalServiceToken) {
        this(new RestTemplate(), baseUrl, internalServiceToken);
    }

    UserClient(RestTemplate restTemplate, String baseUrl, String internalServiceToken) {
        this.restTemplate = restTemplate;
        this.baseUrl = baseUrl;
        this.internalServiceToken = internalServiceToken == null ? "" : internalServiceToken;
    }

    public UserDto getUserById(Long userId) {
        String url = UriComponentsBuilder
                .fromUriString(baseUrl)
                .path("/{userId}")
                .buildAndExpand(userId)
                .toUriString();

        ResponseEntity<UserDto> response = restTemplate.exchange(
                url, HttpMethod.GET, internalRequest(), UserDto.class);
        return response.getBody();
    }

    private HttpEntity<Void> internalRequest() {
        HttpHeaders headers = new HttpHeaders();
        if (!internalServiceToken.isBlank()) {
            headers.set("X-Internal-Service-Token", internalServiceToken);
        }
        return new HttpEntity<>(headers);
    }
}
