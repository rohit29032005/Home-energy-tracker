package com.hometracker.usage_service.controller;
import com.hometracker.usage_service.dto.UsageDto;
import com.hometracker.usage_service.security.UsageAccessVerifier;
import com.hometracker.usage_service.service.UsageService;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/usage")
public class UsageController {

    private final UsageService usageService;
    private final UsageAccessVerifier usageAccessVerifier;

    public UsageController(UsageService usageService, UsageAccessVerifier usageAccessVerifier) {
        this.usageService = usageService;
        this.usageAccessVerifier = usageAccessVerifier;
    }

    @GetMapping("/{userId}")
    public ResponseEntity<UsageDto> getUserDeviceUsage(
            @PathVariable Long userId,
            @RequestParam(defaultValue = "3") int days,
            HttpServletRequest request) {
        UsageAccessVerifier.CallerType caller = usageAccessVerifier.authenticate(request, true);
        usageAccessVerifier.verifyUsageAccess(request, userId, caller);
        final UsageDto usage = usageService.getXDaysUsageForUser(userId, days);
        return ResponseEntity.ok(usage);
    }
}
