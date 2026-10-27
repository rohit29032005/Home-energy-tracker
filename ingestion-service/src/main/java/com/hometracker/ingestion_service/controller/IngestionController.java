package com.hometracker.ingestion_service.controller;

import com.hometracker.ingestion_service.dto.EnergyUsageDto;
import com.hometracker.ingestion_service.service.IngestionService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/ingestion")
public class IngestionController {

    private final IngestionService ingestionService;

    public IngestionController(IngestionService ingestionService) {
        this.ingestionService = ingestionService;
    }

    @PostMapping
    @ResponseStatus(org.springframework.http.HttpStatus.CREATED)
    public void ingestData(@Valid @RequestBody EnergyUsageDto usageDto, HttpServletRequest request) {
        ingestionService.ingestEnergyUsage(usageDto, request);
    }
}
