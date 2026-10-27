package com.hometracker.insight_service.service;

import com.hometracker.insight_service.client.UsageClient;
import com.hometracker.insight_service.config.TariffConfig;
import com.hometracker.insight_service.dto.*;
import lombok.extern.slf4j.Slf4j;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.ai.ollama.OllamaChatModel;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;

@Slf4j
@Service
public class InsightService {

    private final UsageClient usageClient;
    private final BillCalculationService billCalculationService;
    private final TariffConfig tariffConfig;
    private final OllamaChatModel ollamaChatModel;

    public InsightService(UsageClient usageClient,
                          BillCalculationService billCalculationService,
                          TariffConfig tariffConfig,
                          OllamaChatModel ollamaChatModel) {
        this.usageClient = usageClient;
        this.billCalculationService = billCalculationService;
        this.tariffConfig = tariffConfig;
        this.ollamaChatModel = ollamaChatModel;
    }

    /**
     * Month-End Bill Forecast calculation.
     */
    public BillForecastDto getBillForecast(Long userId, int days) {
        int evalDays = Math.max(days, 1);
        UsageDto usageData = fetchUsage(userId, evalDays);

        List<DeviceDto> devices = usageData.devices() == null ? List.of() : usageData.devices();
        double currentKwh = devices.stream().mapToDouble(DeviceDto::energyConsumed).sum();
        double currentKwhRounded = billCalculationService.roundTwoDecimals(currentKwh);

        double dailyRateKwh = billCalculationService.roundTwoDecimals(currentKwhRounded / evalDays);
        double projectedMonthlyKwh = billCalculationService.projectMonthlyKwh(dailyRateKwh);
        double currentEstimatedCost = billCalculationService.calculateBillCost(currentKwhRounded, false);
        double projectedMonthlyCost = billCalculationService.calculateBillCost(projectedMonthlyKwh, true);

        String tariffSummary = String.format(
                "Fixed: $%.2f/mo | Slab 1 (0-%.0fkWh): $%.2f/kWh | Slab 2 (%.0f-%.0fkWh): $%.2f/kWh | Slab 3 (>%.0fkWh): $%.2f/kWh",
                tariffConfig.getFixedCharge(),
                tariffConfig.getSlab1Limit(), tariffConfig.getSlab1Rate(),
                tariffConfig.getSlab1Limit(), tariffConfig.getSlab2Limit(), tariffConfig.getSlab2Rate(),
                tariffConfig.getSlab2Limit(), tariffConfig.getSlab3Rate()
        );

        return BillForecastDto.builder()
                .userId(userId)
                .periodDays(evalDays)
                .currentKwh(currentKwhRounded)
                .currentEstimatedCost(currentEstimatedCost)
                .dailyRateKwh(dailyRateKwh)
                .projectedMonthlyKwh(projectedMonthlyKwh)
                .projectedMonthlyCost(projectedMonthlyCost)
                .tariffSummary(tariffSummary)
                .build();
    }

    /**
     * Appliance Energy Consumption Ranking.
     */
    public ApplianceRankingResultDto getApplianceRanking(Long userId, int days) {
        int evalDays = Math.max(days, 1);
        UsageDto usageData = fetchUsage(userId, evalDays);

        List<DeviceDto> rawDevices = usageData.devices() == null ? List.of() : usageData.devices();
        double totalKwh = rawDevices.stream().mapToDouble(DeviceDto::energyConsumed).sum();
        double totalKwhRounded = billCalculationService.roundTwoDecimals(totalKwh);
        double totalEstimatedCost = billCalculationService.calculateBillCost(totalKwhRounded, false);

        List<ApplianceRankingDto> sortedRankings = rawDevices.stream()
                .sorted(Comparator.comparingDouble(DeviceDto::energyConsumed).reversed())
                .map(d -> {
                    double deviceKwh = billCalculationService.roundTwoDecimals(d.energyConsumed());
                    double pct = totalKwhRounded > 0 ? billCalculationService.roundTwoDecimals((deviceKwh / totalKwhRounded) * 100.0) : 0.0;
                    double cost = totalKwhRounded > 0 ? billCalculationService.roundTwoDecimals((deviceKwh / totalKwhRounded) * totalEstimatedCost) : 0.0;
                    return ApplianceRankingDto.builder()
                            .deviceId(d.id())
                            .name(d.name())
                            .type(d.type())
                            .location(d.location())
                            .energyConsumedKwh(deviceKwh)
                            .percentageOfTotal(pct)
                            .estimatedCost(cost)
                            .build();
                })
                .toList();

        return ApplianceRankingResultDto.builder()
                .userId(userId)
                .periodDays(evalDays)
                .totalKwh(totalKwhRounded)
                .totalEstimatedCost(totalEstimatedCost)
                .rankings(sortedRankings)
                .build();
    }

    /**
     * Standby Energy Detective.
     */
    public StandbyDetectiveDto getStandbyDetective(Long userId, int days) {
        int evalDays = Math.max(days, 1);
        UsageDto usageData = fetchUsage(userId, evalDays);

        List<DeviceDto> devices = usageData.devices() == null ? List.of() : usageData.devices();
        double totalKwh = devices.stream().mapToDouble(DeviceDto::energyConsumed).sum();

        // Estimate baseline continuous power consumption during idle hours (~15% of average load or baseline)
        double totalHours = evalDays * 24.0;
        double averageWatts = (totalKwh / totalHours) * 1000.0;
        double baselineWatts = billCalculationService.roundTwoDecimals(averageWatts * 0.20); // 20% estimated continuous idle

        double standbyDailyKwh = billCalculationService.roundTwoDecimals((baselineWatts * 24.0) / 1000.0);
        double standbyMonthlyKwh = billCalculationService.roundTwoDecimals(standbyDailyKwh * 30.0);
        double standbyMonthlyCost = billCalculationService.calculateBillCost(standbyMonthlyKwh, false);

        String riskLevel = baselineWatts > 150.0 ? "HIGH" : (baselineWatts > 50.0 ? "MEDIUM" : "LOW");

        List<String> recommendations = new ArrayList<>();
        recommendations.add("Plug standby electronics into smart surge protectors or switchable power strips.");
        recommendations.add("Unplug game consoles, soundbars, and second TVs when not in use for extended periods.");
        if (baselineWatts > 100.0) {
            recommendations.add("Check idle desktop computers and set automated sleep timers after 15 minutes.");
        }

        List<String> probableCategories = List.of(
                "Entertainment Systems (TVs, Soundbars, Gaming Consoles)",
                "Home Office Setup (Desktop PCs, Monitors, Printers)",
                "Kitchen Appliances with Digital Displays / Clocks",
                "Continuous Water Dispensers & Idle Chargers"
        );

        String baselineAssumptions = String.format(
                "Baseline load computed as ~20%% continuous idle power during low-activity windows over %d days. Target threshold: <50W continuous idle.",
                evalDays
        );

        return StandbyDetectiveDto.builder()
                .userId(userId)
                .baselineWatts(baselineWatts)
                .standbyDailyKwh(standbyDailyKwh)
                .standbyMonthlyKwh(standbyMonthlyKwh)
                .standbyMonthlyCost(standbyMonthlyCost)
                .riskLevel(riskLevel)
                .recommendations(recommendations)
                .probableCategories(probableCategories)
                .baselineAssumptions(baselineAssumptions)
                .build();
    }

    /**
     * Returns saving tips with deterministic analytics and safe AI fallback.
     */
    public InsightDto getSavingsTips(Long userId) {
        BillForecastDto forecast = getBillForecast(userId, 3);
        ApplianceRankingResultDto rankings = getApplianceRanking(userId, 3);
        StandbyDetectiveDto standby = getStandbyDetective(userId, 3);

        String topApplianceName = rankings.rankings().isEmpty() ? "None" : rankings.rankings().get(0).name();
        double topApplianceKwh = rankings.rankings().isEmpty() ? 0.0 : rankings.rankings().get(0).energyConsumedKwh();

        String prompt = String.format(
                "Household Total Usage (3 days): %.2f kWh. Estimated Current Bill: $%.2f. Projected Monthly Bill: $%.2f. " +
                        "Top Consuming Appliance: %s (%.2f kWh). Standby Idle Load: %.1f W (Risk: %s). " +
                        "Provide 3 concise, highly practical tips to reduce electricity consumption and prevent bill shock.",
                forecast.currentKwh(), forecast.currentEstimatedCost(), forecast.projectedMonthlyCost(),
                topApplianceName, topApplianceKwh, standby.baselineWatts(), standby.riskLevel()
        );

        try {
            log.info("Requesting energy savings recommendations from Ollama AI model for userId {}", userId);
            ChatResponse response = ollamaChatModel.call(Prompt.builder().content(prompt).build());
            String aiTips = response.getResult().getOutput().getText();

            return InsightDto.builder()
                    .userId(userId)
                    .tips(aiTips)
                    .energyUsage(forecast.currentKwh())
                    .estimatedCost(forecast.currentEstimatedCost())
                    .projectedMonthlyCost(forecast.projectedMonthlyCost())
                    .isAiGenerated(true)
                    .standbyRiskLevel(standby.riskLevel())
                    .build();

        } catch (Exception e) {
            log.warn("Ollama AI model unavailable or threw exception for userId {}. Using deterministic fallback tips. Error: {}", userId, e.getMessage());
            String fallbackTips = buildFallbackSavingsTips(forecast, topApplianceName, standby);

            return InsightDto.builder()
                    .userId(userId)
                    .tips(fallbackTips)
                    .energyUsage(forecast.currentKwh())
                    .estimatedCost(forecast.currentEstimatedCost())
                    .projectedMonthlyCost(forecast.projectedMonthlyCost())
                    .isAiGenerated(false)
                    .standbyRiskLevel(standby.riskLevel())
                    .build();
        }
    }

    /**
     * Returns household overview with deterministic analytics and safe AI fallback.
     */
    public InsightDto getOverview(Long userId) {
        BillForecastDto forecast = getBillForecast(userId, 3);
        StandbyDetectiveDto standby = getStandbyDetective(userId, 3);

        String prompt = String.format(
                "Analyze aggregate 3-day household usage data: %.2f kWh used, current cost $%.2f, projected monthly cost $%.2f. " +
                        "Provide a 2-sentence executive summary of electricity consumption.",
                forecast.currentKwh(), forecast.currentEstimatedCost(), forecast.projectedMonthlyCost()
        );

        try {
            log.info("Requesting executive usage overview from Ollama AI model for userId {}", userId);
            ChatResponse response = ollamaChatModel.call(Prompt.builder().content(prompt).build());
            String aiSummary = response.getResult().getOutput().getText();

            return InsightDto.builder()
                    .userId(userId)
                    .tips(aiSummary)
                    .energyUsage(forecast.currentKwh())
                    .estimatedCost(forecast.currentEstimatedCost())
                    .projectedMonthlyCost(forecast.projectedMonthlyCost())
                    .isAiGenerated(true)
                    .standbyRiskLevel(standby.riskLevel())
                    .build();

        } catch (Exception e) {
            log.warn("Ollama AI model unavailable for userId {}. Using deterministic overview summary.", userId);
            String fallbackSummary = String.format(
                    "3-day consumption total is %.2f kWh with an estimated cost of $%.2f. Based on current consumption rates, your projected 30-day bill is $%.2f with a %s standby load risk (%.1fW continuous idle).",
                    forecast.currentKwh(), forecast.currentEstimatedCost(), forecast.projectedMonthlyCost(), standby.riskLevel(), standby.baselineWatts()
            );

            return InsightDto.builder()
                    .userId(userId)
                    .tips(fallbackSummary)
                    .energyUsage(forecast.currentKwh())
                    .estimatedCost(forecast.currentEstimatedCost())
                    .projectedMonthlyCost(forecast.projectedMonthlyCost())
                    .isAiGenerated(false)
                    .standbyRiskLevel(standby.riskLevel())
                    .build();
        }
    }

    private UsageDto fetchUsage(Long userId, int days) {
        try {
            UsageDto dto = usageClient.getXDaysUsageForUser(userId, days);
            return dto != null ? dto : UsageDto.builder().userId(userId).devices(List.of()).build();
        } catch (Exception e) {
            log.warn("Failed to fetch usage data from Usage Service for userId {}: {}", userId, e.getMessage());
            return UsageDto.builder().userId(userId).devices(List.of()).build();
        }
    }

    private String buildFallbackSavingsTips(BillForecastDto forecast, String topAppliance, StandbyDetectiveDto standby) {
        StringBuilder sb = new StringBuilder();
        sb.append("💡 **Deterministic Energy Savings Recommendations**\n\n");
        sb.append(String.format("1. **Top Power Consumer (%s):** Focus on optimizing operation hours for your highest consuming appliance.\n", topAppliance));
        sb.append(String.format("2. **Standby Phantom Load (%s Risk - %.1fW):** Unplug entertainment systems and home office setups when idle to save up to $%.2f/month.\n", standby.riskLevel(), standby.baselineWatts(), standby.standbyMonthlyCost()));
        sb.append(String.format("3. **Bill Shock Prevention:** At your current rate of %.2f kWh/day, your projected 30-day bill will reach $%.2f. Shifting heavy loads to off-peak hours can help stay within lower tariff slabs.", forecast.dailyRateKwh(), forecast.projectedMonthlyCost()));
        return sb.toString();
    }
}