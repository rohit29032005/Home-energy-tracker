package com.hometracker.user_service.dto;


import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.PositiveOrZero;
import lombok.*;


@NoArgsConstructor
@AllArgsConstructor
@Data
@Builder
public class UserDto {
    private Long id;
    
    @NotBlank(message = "Name is required")
    private String name;
    
    private String surname;
    
    @NotBlank(message = "Email is required")
    @Email(message = "Must be a valid email address")
    private String email;
    
    private String address;
    private boolean alerting;
    
    @PositiveOrZero(message = "Energy alerting threshold must be zero or positive")
    private double energyAlertingThreshold;
}

