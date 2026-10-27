package com.hometracker.alert_service.client;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

/** Retrieves device ownership and notification address for an anomaly event. */
@Component
public class AlertContextClient {
    private final RestTemplate restTemplate;
    private final String deviceServiceUrl;
    private final String userServiceUrl;
    private final String internalServiceToken;

    @Autowired
    public AlertContextClient(@Value("${device.service.url}") String deviceServiceUrl,
                              @Value("${user.service.url}") String userServiceUrl,
                              @Value("${internal.service.token:}") String internalServiceToken) {
        this(new RestTemplate(), deviceServiceUrl, userServiceUrl, internalServiceToken);
    }

    AlertContextClient(RestTemplate restTemplate,
                       String deviceServiceUrl,
                       String userServiceUrl,
                       String internalServiceToken) {
        this.restTemplate = restTemplate;
        this.deviceServiceUrl = deviceServiceUrl;
        this.userServiceUrl = userServiceUrl;
        this.internalServiceToken = internalServiceToken == null ? "" : internalServiceToken;
    }

    public DeviceReference getDevice(Long deviceId) {
        ResponseEntity<DeviceReference> response = restTemplate.exchange(
                deviceServiceUrl + "/" + deviceId, HttpMethod.GET, internalRequest(), DeviceReference.class);
        return response.getBody();
    }

    public UserReference getUser(Long userId) {
        ResponseEntity<UserReference> response = restTemplate.exchange(
                userServiceUrl + "/" + userId, HttpMethod.GET, internalRequest(), UserReference.class);
        return response.getBody();
    }

    private HttpEntity<Void> internalRequest() {
        HttpHeaders headers = new HttpHeaders();
        if (!internalServiceToken.isBlank()) {
            headers.set("X-Internal-Service-Token", internalServiceToken);
        }
        return new HttpEntity<>(headers);
    }

    public record DeviceReference(Long id, Long userId) { }
    public record UserReference(Long id, String email, boolean alerting) { }
}
