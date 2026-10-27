package com.hometracker.device_service.dto;

import com.hometracker.device_service.model.DeviceType;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@AllArgsConstructor
@NoArgsConstructor
@Builder
@Data
public class DeviceDto {
    private Long id;
    
    @NotBlank(message = "Device name is required")
    private String name;
    
    @NotNull(message = "Device type is required")
    private DeviceType type;
    
    private String location;
    
    @NotNull(message = "User ID is required")
    private Long userId;
}

