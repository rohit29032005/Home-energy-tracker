package com.hometracker.insight_service.service;

import com.hometracker.insight_service.config.TariffConfig;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class BillCalculationServiceTest {

    private BillCalculationService billCalculationService;
    private TariffConfig tariffConfig;

    @BeforeEach
    void setUp() {
        // Fixed: $10.00, Slab1: 0-100 @ $0.12, Slab2: 101-300 @ $0.18, Slab3: >300 @ $0.25
        tariffConfig = new TariffConfig(10.00, 100.0, 0.12, 300.0, 0.18, 0.25);
        billCalculationService = new BillCalculationService(tariffConfig);
    }

    @Test
    void testZeroUsageWithFixedCharge() {
        double cost = billCalculationService.calculateBillCost(0, true);
        assertEquals(10.00, cost);
    }

    @Test
    void testZeroUsageWithoutFixedCharge() {
        double cost = billCalculationService.calculateBillCost(0, false);
        assertEquals(0.00, cost);
    }

    @Test
    void testSlab1Usage() {
        // 50 kWh @ 0.12 = $6.00
        double cost = billCalculationService.calculateBillCost(50, false);
        assertEquals(6.00, cost);
    }

    @Test
    void testSlab2Usage() {
        // 100 kWh @ 0.12 ($12.00) + 100 kWh @ 0.18 ($18.00) = $30.00
        double cost = billCalculationService.calculateBillCost(200, false);
        assertEquals(30.00, cost);
    }

    @Test
    void testSlab3Usage() {
        // 100 kWh @ 0.12 ($12) + 200 kWh @ 0.18 ($36) + 100 kWh @ 0.25 ($25) = $73.00
        double cost = billCalculationService.calculateBillCost(400, false);
        assertEquals(73.00, cost);
    }

    @Test
    void testProjectMonthlyKwh() {
        // 10 kWh/day * 30 days = 300 kWh
        double projected = billCalculationService.projectMonthlyKwh(10.0);
        assertEquals(300.0, projected);
    }

    @Test
    void testCalculateBaselineWatts() {
        // 0.5 kWh over 5 hours = 0.1 kW = 100 Watts
        double watts = billCalculationService.calculateBaselineWatts(0.5, 5.0);
        assertEquals(100.0, watts);
    }
}
