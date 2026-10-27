package com.hometracker.alert_service.service;

import io.micrometer.core.instrument.MeterRegistry;
import org.springframework.stereotype.Component;

/** Prometheus-exported counters for alert creation, suppression, and attempted-delivery failures. */
@Component
public class AlertMetrics {
    private final MeterRegistry meterRegistry;

    public AlertMetrics(MeterRegistry meterRegistry) {
        this.meterRegistry = meterRegistry;
    }

    public void created(String alertType) {
        meterRegistry.counter("home_energy_alerts_created_total", "alert_type", alertType).increment();
    }

    public void suppressed(String alertType) {
        meterRegistry.counter("home_energy_alerts_suppressed_total", "alert_type", alertType).increment();
    }

    /**
     * Counts a failed SMTP attempt separately from alert creation. An unsent
     * alert row is retained by {@link AlertService}, so this counter gives
     * operators a way to distinguish a stored alert from a delivered email.
     */
    public void deliveryFailed(String alertType) {
        meterRegistry.counter("home_energy_alerts_delivery_failures_total", "alert_type", alertType).increment();
    }
}
