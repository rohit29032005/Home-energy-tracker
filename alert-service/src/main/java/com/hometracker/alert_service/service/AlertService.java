package com.hometracker.alert_service.service;

import com.hometracker.alert_service.client.AlertContextClient;
import com.hometracker.alert_service.entity.Alert;
import com.hometracker.alert_service.kafka.event.AnomalyResultEvent;
import com.hometracker.alert_service.repository.AlertRepository;
import com.hometracker.kafka.event.AlertingEvent;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Service;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.List;

/**
 * Stores and sends one notification for a distinct alert key in the configured
 * window. The key is user + device-or-household + alert type, so one device or
 * one user cannot suppress another resource's alert.
 */
@Slf4j
@Service
public class AlertService {

    private final EmailService emailService;
    private final AlertRepository alertRepository;
    private final AlertContextClient alertContextClient;
    private final AlertMetrics alertMetrics;
    private final boolean deduplicationEnabled;
    private final long deduplicationWindowMinutes;

    public AlertService(EmailService emailService,
                        AlertRepository alertRepository,
                        AlertContextClient alertContextClient,
                        AlertMetrics alertMetrics,
                        @Value("${alerts.deduplication.enabled:true}") boolean deduplicationEnabled,
                        @Value("${alerts.deduplication.window-minutes:15}") long deduplicationWindowMinutes) {
        this.emailService = emailService;
        this.alertRepository = alertRepository;
        this.alertContextClient = alertContextClient;
        this.alertMetrics = alertMetrics;
        this.deduplicationEnabled = deduplicationEnabled;
        this.deduplicationWindowMinutes = deduplicationWindowMinutes;
    }

    @KafkaListener(topics = "energy-alerts", groupId = "alert-service")
    public void energyUsageAlertEvent(AlertingEvent event) {
        processAlert(
                event.getUserId(),
                event.getDeviceId(),
                event.getAlertType() == null ? "THRESHOLD" : event.getAlertType(),
                event.getMessage(),
                event.getThreshold(),
                event.getEnergyConsumed(),
                event.getEmail());
    }

    @KafkaListener(
            topics = "anomaly-results",
            groupId = "alert-service-anomaly",
            properties = "spring.json.value.default.type=com.hometracker.alert_service.kafka.event.AnomalyResultEvent")
    public void anomalyResultEvent(AnomalyResultEvent event) {
        if (!event.isAnomaly()) {
            log.info("ML result for device {} is normal; no alert is created", event.getDeviceId());
            return;
        }
        try {
            AlertContextClient.DeviceReference device = alertContextClient.getDevice(event.getDeviceId());
            AlertContextClient.UserReference user = alertContextClient.getUser(device.userId());
            if (user == null || !user.alerting()) {
                log.info("ML anomaly for device {} has no alert-enabled owner", event.getDeviceId());
                return;
            }
            processAlert(
                    user.id(),
                    device.id(),
                    "ML_ANOMALY",
                    "ML anomaly detected by " + event.getModelVersion() + " (probability=" + event.getAnomalyProbability() + ")",
                    event.getDecisionThreshold(),
                    event.getAnomalyProbability(),
                    user.email());
        } catch (Exception exception) {
            // The Kafka listener must remain available; the failure is explicit in service logs.
            log.error("Could not resolve ownership for ML anomaly on device {}", event.getDeviceId(), exception);
        }
    }

    public boolean processAlert(Long userId,
                                Long deviceId,
                                String alertType,
                                String message,
                                double threshold,
                                double energyConsumed,
                                String email) {
        String deduplicationKey = userId + ":" + (deviceId == null ? "HOUSEHOLD" : deviceId) + ":" + alertType;
        LocalDateTime now = LocalDateTime.now();
        if (deduplicationEnabled && alertRepository.findTopByDeduplicationKeyOrderByCreatedAtDesc(deduplicationKey)
                .filter(existing -> Duration.between(existing.getCreatedAt(), now).toMinutes() < deduplicationWindowMinutes)
                .isPresent()) {
            log.info("Suppressed duplicate alert with key {} inside {} minutes", deduplicationKey, deduplicationWindowMinutes);
            alertMetrics.suppressed(alertType);
            return false;
        }

        Alert alert = Alert.builder()
                .userId(userId)
                .deviceId(deviceId)
                .message(message)
                .alertType(alertType)
                .deduplicationKey(deduplicationKey)
                .threshold(threshold)
                .energyConsumed(energyConsumed)
                .email(email)
                .createdAt(now)
                .sent(false)
                .build();
        Alert saved = alertRepository.save(alert);
        boolean deliveryAttempted = email != null && !email.isBlank();
        boolean sent = deliveryAttempted && emailService.sendEmail(
                email,
                "Energy Usage Alert for User " + userId,
                "Alert: " + message + "\nThreshold: " + threshold + "\nEnergy Consumed: " + energyConsumed);
        saved.setSent(sent);
        alertRepository.save(saved);
        alertMetrics.created(alertType);
        if (deliveryAttempted && !sent) {
            alertMetrics.deliveryFailed(alertType);
        }
        return true;
    }

    public List<Alert> getAlertsByUserId(Long userId) {
        return alertRepository.findByUserIdOrderByCreatedAtDesc(userId);
    }

    public List<Alert> getAllAlerts() {
        return alertRepository.findAll();
    }
}

