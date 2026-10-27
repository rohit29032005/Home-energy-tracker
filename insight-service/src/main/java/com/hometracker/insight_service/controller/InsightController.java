package com.hometracker.insight_service.controller;

import com.hometracker.insight_service.dto.*;
import com.hometracker.insight_service.security.GatewayOwnershipVerifier;
import com.hometracker.insight_service.service.InsightService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/insight")
public class InsightController {

    private final InsightService insightService;
    private final GatewayOwnershipVerifier gatewayOwnershipVerifier;

    public InsightController(InsightService insightService,
                             GatewayOwnershipVerifier gatewayOwnershipVerifier) {
        this.insightService = insightService;
        this.gatewayOwnershipVerifier = gatewayOwnershipVerifier;
    }

    @GetMapping("/saving-tips/{userId}")
    public ResponseEntity<InsightDto> getSavingTips(@PathVariable Long userId,
                                                     HttpServletRequest request) {
        gatewayOwnershipVerifier.verifyGatewayOwnership(request, userId);
        final InsightDto insight = insightService.getSavingsTips(userId);
        return ResponseEntity.ok(insight);
    }

    @GetMapping("/overview/{userId}")
    public ResponseEntity<InsightDto> getOverview(@PathVariable Long userId,
                                                   HttpServletRequest request) {
        gatewayOwnershipVerifier.verifyGatewayOwnership(request, userId);
        final InsightDto insight = insightService.getOverview(userId);
        return ResponseEntity.ok(insight);
    }

    @GetMapping("/bill-forecast/{userId}")
    public ResponseEntity<BillForecastDto> getBillForecast(
            @PathVariable Long userId,
            @RequestParam(defaultValue = "3") int days,
            HttpServletRequest request) {
        gatewayOwnershipVerifier.verifyGatewayOwnership(request, userId);
        final BillForecastDto forecast = insightService.getBillForecast(userId, days);
        return ResponseEntity.ok(forecast);
    }

    @GetMapping("/appliance-ranking/{userId}")
    public ResponseEntity<ApplianceRankingResultDto> getApplianceRanking(
            @PathVariable Long userId,
            @RequestParam(defaultValue = "3") int days,
            HttpServletRequest request) {
        gatewayOwnershipVerifier.verifyGatewayOwnership(request, userId);
        final ApplianceRankingResultDto ranking = insightService.getApplianceRanking(userId, days);
        return ResponseEntity.ok(ranking);
    }

    @GetMapping("/standby-detective/{userId}")
    public ResponseEntity<StandbyDetectiveDto> getStandbyDetective(
            @PathVariable Long userId,
            @RequestParam(defaultValue = "3") int days,
            HttpServletRequest request) {
        gatewayOwnershipVerifier.verifyGatewayOwnership(request, userId);
        final StandbyDetectiveDto standby = insightService.getStandbyDetective(userId, days);
        return ResponseEntity.ok(standby);
    }
}
