package com.hometracker.insight_service.service;

import com.hometracker.insight_service.config.TariffConfig;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;

@Service
public class BillCalculationService {

    private final TariffConfig tariffConfig;

    public BillCalculationService(TariffConfig tariffConfig) {
        this.tariffConfig = tariffConfig;
    }

    /**
     * Calculates the estimated energy bill for a given consumption in kWh using tiered tariff slabs.
     * Fixed monthly supply charge is included when includeFixedCharge is true.
     */
    public double calculateBillCost(double kwh, boolean includeFixedCharge) {
        if (kwh <= 0) {
            return includeFixedCharge ? roundTwoDecimals(tariffConfig.getFixedCharge()) : 0.0;
        }

        double cost = 0.0;
        double remainingKwh = kwh;

        // Slab 1: 0 to slab1Limit (e.g. 0-100 kWh)
        double slab1Usage = Math.min(remainingKwh, tariffConfig.getSlab1Limit());
        cost += slab1Usage * tariffConfig.getSlab1Rate();
        remainingKwh -= slab1Usage;

        // Slab 2: slab1Limit to slab2Limit (e.g. 101-300 kWh)
        if (remainingKwh > 0) {
            double slab2Capacity = tariffConfig.getSlab2Limit() - tariffConfig.getSlab1Limit();
            double slab2Usage = Math.min(remainingKwh, slab2Capacity);
            cost += slab2Usage * tariffConfig.getSlab2Rate();
            remainingKwh -= slab2Usage;
        }

        // Slab 3: > slab2Limit (e.g. >300 kWh)
        if (remainingKwh > 0) {
            cost += remainingKwh * tariffConfig.getSlab3Rate();
        }

        if (includeFixedCharge) {
            cost += tariffConfig.getFixedCharge();
        }

        return roundTwoDecimals(cost);
    }

    /**
     * Projects 30-day month-end consumption in kWh based on average daily consumption rate.
     */
    public double projectMonthlyKwh(double dailyRateKwh) {
        if (dailyRateKwh <= 0) return 0.0;
        return roundTwoDecimals(dailyRateKwh * 30.0);
    }

    /**
     * Calculates baseline continuous power consumption in Watts.
     */
    public double calculateBaselineWatts(double lowActivityKwh, double periodHours) {
        if (periodHours <= 0 || lowActivityKwh <= 0) return 0.0;
        return roundTwoDecimals((lowActivityKwh / periodHours) * 1000.0);
    }

    public double roundTwoDecimals(double value) {
        return BigDecimal.valueOf(value)
                .setScale(2, RoundingMode.HALF_UP)
                .doubleValue();
    }
}
