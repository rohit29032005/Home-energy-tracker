package com.hometracker.device_service.controller;

import com.hometracker.device_service.dto.DeviceDto;
import com.hometracker.device_service.security.OwnershipVerifier;
import com.hometracker.device_service.service.DeviceService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/device")
public class DeviceController {

    private DeviceService deviceService;
    private final OwnershipVerifier ownershipVerifier;

    public DeviceController(DeviceService deviceService, OwnershipVerifier ownershipVerifier) {
        this.deviceService = deviceService;
        this.ownershipVerifier = ownershipVerifier;
    }

    @GetMapping("/{id}")
    public ResponseEntity<DeviceDto> getDeviceById(@PathVariable Long id, HttpServletRequest request) {
        OwnershipVerifier.CallerType caller = ownershipVerifier.authenticate(request, true);
        DeviceDto device = deviceService.getDeviceById(id);
        ownershipVerifier.verifyOwnershipForGateway(request, device.getUserId(), caller);
        return ResponseEntity.ok(device);
    }

    @PostMapping({"", "/create"})
    public ResponseEntity<DeviceDto> createDevice(@Valid @RequestBody DeviceDto deviceDto, HttpServletRequest request) {
        OwnershipVerifier.CallerType caller = ownershipVerifier.authenticate(request, false);
        ownershipVerifier.verifyOwnershipForGateway(request, deviceDto.getUserId(), caller);
        DeviceDto createdDevice = deviceService.createDevice(deviceDto);
        return ResponseEntity.ok(createdDevice);
    }

    @PutMapping("/{id}")
    public ResponseEntity<DeviceDto> updateDevice(
            @PathVariable Long id, @Valid @RequestBody DeviceDto deviceDto, HttpServletRequest request) {
        // Existing ownership is checked before an update, preventing user-id reassignment.
        OwnershipVerifier.CallerType caller = ownershipVerifier.authenticate(request, false);
        DeviceDto existing = deviceService.getDeviceById(id);
        ownershipVerifier.verifyOwnershipForGateway(request, existing.getUserId(), caller);
        ownershipVerifier.verifyOwnershipForGateway(request, deviceDto.getUserId(), caller);
        DeviceDto updatedDevice = deviceService.updateDevice(id, deviceDto);
        return ResponseEntity.ok(updatedDevice);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteDevice(@PathVariable Long id, HttpServletRequest request) {
        OwnershipVerifier.CallerType caller = ownershipVerifier.authenticate(request, false);
        DeviceDto existing = deviceService.getDeviceById(id);
        ownershipVerifier.verifyOwnershipForGateway(request, existing.getUserId(), caller);
        deviceService.deleteDevice(id);
        return ResponseEntity.noContent().build();
    }

    @GetMapping("/user/{userId}")
    public ResponseEntity<List<DeviceDto>> getAllDevicesByUserId(
            @PathVariable Long userId, HttpServletRequest request) {
        OwnershipVerifier.CallerType caller = ownershipVerifier.authenticate(request, true);
        ownershipVerifier.verifyOwnershipForGateway(request, userId, caller);
        List<DeviceDto> devices = deviceService.getAllDevicesByUserId(userId);
        return ResponseEntity.ok(devices);
    }
}
