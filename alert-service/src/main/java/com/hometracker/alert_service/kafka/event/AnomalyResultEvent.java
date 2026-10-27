package com.hometracker.alert_service.kafka.event;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import lombok.Data;

import java.time.Instant;

/** JSON event published by the Python ML service to the anomaly-results topic. */
@Data
@JsonIgnoreProperties(ignoreUnknown = true)
public class AnomalyResultEvent {
    private Long deviceId;
    private boolean anomaly;
    private double anomalyProbability;
    private String modelVersion;
    private double decisionThreshold;
    private Instant timestamp;
}
