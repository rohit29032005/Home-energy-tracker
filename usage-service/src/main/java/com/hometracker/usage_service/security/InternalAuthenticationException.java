package com.hometracker.usage_service.security;

/**
 * Raised when a request to a private Usage Service endpoint does not carry a
 * valid trusted-caller credential.
 */
public class InternalAuthenticationException extends RuntimeException {
    public InternalAuthenticationException(String message) {
        super(message);
    }
}
