package com.hometracker.insight_service.dto;

import lombok.Builder;

import java.util.List;

@Builder
public record ApplianceRankingResultDto(
        Long userId,
        int periodDays,
        double totalKwh,
        double totalEstimatedCost,
        List<ApplianceRankingDto> rankings
) {
}
