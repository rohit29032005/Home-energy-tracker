package com.hometracker.insight_service.dto;

import lombok.Builder;

@Builder
public record InsightDto(
        Long userId,
        String tips,
        double energyUsage,
        double estimatedCost,
        double projectedMonthlyCost,
        boolean isAiGenerated,
        String standbyRiskLevel
) {
}
