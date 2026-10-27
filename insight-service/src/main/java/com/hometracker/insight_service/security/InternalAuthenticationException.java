package com.hometracker.insight_service.security;

/**
 * Raised when a request reaching a private service cannot prove that it was
 * forwarded by the API gateway.
 */
public class InternalAuthenticationException extends RuntimeException {

    public InternalAuthenticationException(String message) {
        super(message);
    }
}
