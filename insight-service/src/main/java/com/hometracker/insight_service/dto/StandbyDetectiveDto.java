package com.hometracker.insight_service.dto;

import lombok.Builder;

import java.util.List;

@Builder
public record StandbyDetectiveDto(
        Long userId,
        double baselineWatts,
        double standbyDailyKwh,
        double standbyMonthlyKwh,
        double standbyMonthlyCost,
        String riskLevel, // LOW, MEDIUM, HIGH
        List<String> recommendations,
        List<String> probableCategories,
        String baselineAssumptions
) {
}
