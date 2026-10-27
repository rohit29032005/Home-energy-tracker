package com.hometracker.insight_service.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
@Getter
@Setter
public class TariffConfig {

    private final double fixedCharge;
    private final double slab1Limit;
    private final double slab1Rate;
    private final double slab2Limit;
    private final double slab2Rate;
    private final double slab3Rate;

    public TariffConfig(
            @Value("${tariff.fixed-charge:10.00}") double fixedCharge,
            @Value("${tariff.slab1-limit:100.0}") double slab1Limit,
            @Value("${tariff.slab1-rate:0.12}") double slab1Rate,
            @Value("${tariff.slab2-limit:300.0}") double slab2Limit,
            @Value("${tariff.slab2-rate:0.18}") double slab2Rate,
            @Value("${tariff.slab3-rate:0.25}") double slab3Rate) {
        this.fixedCharge = fixedCharge;
        this.slab1Limit = slab1Limit;
        this.slab1Rate = slab1Rate;
        this.slab2Limit = slab2Limit;
        this.slab2Rate = slab2Rate;
        this.slab3Rate = slab3Rate;
    }
}
