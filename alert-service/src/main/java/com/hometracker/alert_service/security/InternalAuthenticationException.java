package com.hometracker.alert_service.security;

public class InternalAuthenticationException extends RuntimeException {
    public InternalAuthenticationException(String message) {
        super(message);
    }
}
