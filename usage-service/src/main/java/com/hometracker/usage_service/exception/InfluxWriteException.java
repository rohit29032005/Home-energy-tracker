package com.hometracker.usage_service.exception;

/**
 * Signals that a consumed energy event was not durably written to InfluxDB.
 *
 * This must escape the Kafka listener so the configured error handler can
 * retry the record or route a permanently failing record to the DLT. It is
 * deliberately distinct from request-validation failures.
 */
public class InfluxWriteException extends RuntimeException {

    public InfluxWriteException(String message, Throwable cause) {
        super(message, cause);
    }
}
