package com.hometracker.insight_service.security;

/**
 * Raised when a gateway-authenticated user attempts to access another user's
 * insight resource.
 */
public class ResourceOwnershipException extends RuntimeException {

    public ResourceOwnershipException(String message) {
        super(message);
    }
}
