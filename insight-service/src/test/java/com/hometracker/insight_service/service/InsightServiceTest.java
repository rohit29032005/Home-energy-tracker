package com.hometracker.insight_service.service;

import com.hometracker.insight_service.client.UsageClient;
import com.hometracker.insight_service.config.TariffConfig;
import com.hometracker.insight_service.dto.*;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.ai.ollama.OllamaChatModel;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class InsightServiceTest {

    @Mock
    private UsageClient usageClient;

    @Mock
    private OllamaChatModel ollamaChatModel;

    private TariffConfig tariffConfig;
    private BillCalculationService billCalculationService;
    private InsightService insightService;

    @BeforeEach
    void setUp() {
        tariffConfig = new TariffConfig(10.00, 100.0, 0.12, 300.0, 0.18, 0.25);
        billCalculationService = new BillCalculationService(tariffConfig);
        insightService = new InsightService(usageClient, billCalculationService, tariffConfig, ollamaChatModel);
    }

    @Test
    void testGetBillForecast() {
        DeviceDto d1 = DeviceDto.builder().id(1L).name("Refrigerator").type("Kitchen").location("Kitchen").energyConsumed(30.0).build();
        DeviceDto d2 = DeviceDto.builder().id(2L).name("Air Conditioner").type("HVAC").location("Bedroom").energyConsumed(60.0).build();

        when(usageClient.getXDaysUsageForUser(1L, 3))
                .thenReturn(UsageDto.builder().userId(1L).devices(List.of(d1, d2)).build());

        BillForecastDto forecast = insightService.getBillForecast(1L, 3);

        assertNotNull(forecast);
        assertEquals(90.0, forecast.currentKwh());
        assertEquals(30.0, forecast.dailyRateKwh()); // 90 / 3
        assertEquals(900.0, forecast.projectedMonthlyKwh()); // 30 * 30
        assertTrue(forecast.projectedMonthlyCost() > 0);
    }

    @Test
    void testGetApplianceRanking() {
        DeviceDto d1 = DeviceDto.builder().id(1L).name("Fridge").type("Kitchen").location("Kitchen").energyConsumed(20.0).build();
        DeviceDto d2 = DeviceDto.builder().id(2L).name("AC").type("HVAC").location("Bedroom").energyConsumed(80.0).build();

        when(usageClient.getXDaysUsageForUser(1L, 3))
                .thenReturn(UsageDto.builder().userId(1L).devices(List.of(d1, d2)).build());

        ApplianceRankingResultDto result = insightService.getApplianceRanking(1L, 3);

        assertNotNull(result);
        assertEquals(100.0, result.totalKwh());
        assertEquals(2, result.rankings().size());
        assertEquals("AC", result.rankings().get(0).name()); // AC should be #1
        assertEquals(80.0, result.rankings().get(0).percentageOfTotal());
        assertEquals("Fridge", result.rankings().get(1).name()); // Fridge #2
    }

    @Test
    void testGetStandbyDetective() {
        DeviceDto d1 = DeviceDto.builder().id(1L).name("TV").type("Entertainment").location("Living Room").energyConsumed(30.0).build();

        when(usageClient.getXDaysUsageForUser(1L, 3))
                .thenReturn(UsageDto.builder().userId(1L).devices(List.of(d1)).build());

        StandbyDetectiveDto standby = insightService.getStandbyDetective(1L, 3);

        assertNotNull(standby);
        assertTrue(standby.baselineWatts() >= 0);
        assertNotNull(standby.riskLevel());
        assertFalse(standby.recommendations().isEmpty());
    }

    @Test
    void testGetSavingsTipsFallbackWhenAiFails() {
        DeviceDto d1 = DeviceDto.builder().id(1L).name("TV").type("Entertainment").location("Living").energyConsumed(10.0).build();

        when(usageClient.getXDaysUsageForUser(1L, 3))
                .thenReturn(UsageDto.builder().userId(1L).devices(List.of(d1)).build());

        when(ollamaChatModel.call(any(Prompt.class)))
                .thenThrow(new RuntimeException("Ollama model connection refused"));

        InsightDto insight = insightService.getSavingsTips(1L);

        assertNotNull(insight);
        assertFalse(insight.isAiGenerated()); // AI fallback flag should be false
        assertTrue(insight.tips().contains("Deterministic Energy Savings Recommendations"));
        assertEquals(10.0, insight.energyUsage());
    }
}
