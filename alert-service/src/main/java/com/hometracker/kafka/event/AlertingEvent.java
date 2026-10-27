package com.hometracker.kafka.event;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class AlertingEvent {
    private Long userId;
    private Long deviceId;
    private String message;
    private String alertType;
    private double threshold;
    private double energyConsumed;
    private String email;
}
