package com.hometracker.insight_service.dto;

import lombok.Builder;

@Builder
public record BillForecastDto(
        Long userId,
        int periodDays,
        double currentKwh,
        double currentEstimatedCost,
        double dailyRateKwh,
        double projectedMonthlyKwh,
        double projectedMonthlyCost,
        String tariffSummary
) {
}
