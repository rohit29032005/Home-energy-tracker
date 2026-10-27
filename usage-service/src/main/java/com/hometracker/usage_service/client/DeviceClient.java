package com.hometracker.usage_service.client;

import com.hometracker.usage_service.dto.DeviceDto;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.util.UriComponentsBuilder;

import java.util.List;

@Component
public class DeviceClient {

    private final RestTemplate restTemplate;

    private final String baseUrl;
    private final String internalServiceToken;

    @Autowired
    public DeviceClient(@Value("${device.service.url}") String baseUrl,
                        @Value("${internal.service.token:}") String internalServiceToken) {
        this(new RestTemplate(), baseUrl, internalServiceToken);
    }

    DeviceClient(RestTemplate restTemplate, String baseUrl, String internalServiceToken) {
        this.restTemplate = restTemplate;
        this.baseUrl = baseUrl;
        this.internalServiceToken = internalServiceToken == null ? "" : internalServiceToken;
    }

    public DeviceDto getDeviceById (Long deviceId) {
        String url = UriComponentsBuilder
                .fromUriString(baseUrl)
                .path("/{deviceId}")
                .buildAndExpand(deviceId)
                .toUriString();

        ResponseEntity<DeviceDto> response = restTemplate.exchange(
                url, HttpMethod.GET, internalRequest(), DeviceDto.class);
        return response.getBody();
    }

    public List<DeviceDto> getAllDevicesForUser(Long userId) {
        String url = UriComponentsBuilder
                .fromUriString(baseUrl)
                .path("/user/{userId}")
                .buildAndExpand(userId)
                .toUriString();

        ResponseEntity<DeviceDto[]> response = restTemplate.exchange(
                url, HttpMethod.GET, internalRequest(), DeviceDto[].class);
        DeviceDto[] devices = response.getBody();
        return devices == null ? List.of() : List.of(devices);
    }

    private HttpEntity<Void> internalRequest() {
        HttpHeaders headers = new HttpHeaders();
        if (!internalServiceToken.isBlank()) {
            headers.set("X-Internal-Service-Token", internalServiceToken);
        }
        return new HttpEntity<>(headers);
    }
}
