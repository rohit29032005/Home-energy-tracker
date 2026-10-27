package com.hometracker.user_service.security;

public class ResourceOwnershipException extends RuntimeException {
    public ResourceOwnershipException(String message) {
        super(message);
    }
}
