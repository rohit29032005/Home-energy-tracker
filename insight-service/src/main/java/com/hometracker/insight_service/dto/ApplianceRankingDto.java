package com.hometracker.insight_service.dto;

import lombok.Builder;

@Builder
public record ApplianceRankingDto(
        Long deviceId,
        String name,
        String type,
        String location,
        double energyConsumedKwh,
        double percentageOfTotal,
        double estimatedCost
) {
}
