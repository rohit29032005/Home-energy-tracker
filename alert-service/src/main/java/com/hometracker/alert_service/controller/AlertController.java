package com.hometracker.alert_service.controller;

import com.hometracker.alert_service.entity.Alert;
import com.hometracker.alert_service.security.AlertApiAuthorizationVerifier;
import com.hometracker.alert_service.service.AlertService;
import com.hometracker.kafka.event.AlertingEvent;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/alert")
public class AlertController {

    private final AlertService alertService;
    private final AlertApiAuthorizationVerifier authorizationVerifier;

    public AlertController(AlertService alertService,
                           AlertApiAuthorizationVerifier authorizationVerifier) {
        this.alertService = alertService;
        this.authorizationVerifier = authorizationVerifier;
    }

    @PostMapping("/test-send")
    public ResponseEntity<String> sendTestAlert(@RequestBody AlertingEvent alertingEvent,
                                                HttpServletRequest request) {
        authorizationVerifier.verifyGatewayAdmin(request);
        alertService.energyUsageAlertEvent(alertingEvent);
        return ResponseEntity.ok("Alert email dispatched to Mailpit successfully!");
    }

    @GetMapping("/user/{userId}")
    public ResponseEntity<List<Alert>> getAlertsByUserId(@PathVariable Long userId,
                                                         HttpServletRequest request) {
        authorizationVerifier.verifyUserAlertAccess(request, userId);
        List<Alert> alerts = alertService.getAlertsByUserId(userId);
        return ResponseEntity.ok(alerts);
    }

    @GetMapping
    public ResponseEntity<List<Alert>> getAllAlerts(HttpServletRequest request) {
        authorizationVerifier.verifyGatewayAdmin(request);
        List<Alert> alerts = alertService.getAllAlerts();
        return ResponseEntity.ok(alerts);
    }
}
