package com.hometracker.alert_service.security;

public class ResourceOwnershipException extends RuntimeException {
    public ResourceOwnershipException(String message) {
        super(message);
    }
}
