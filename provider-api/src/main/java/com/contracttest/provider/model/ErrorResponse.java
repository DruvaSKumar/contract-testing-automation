/*
 * ============================================================
 * ErrorResponse.java — Standardized Error Response Model
 * ============================================================
 * When something goes wrong (invalid input, resource not found,
 * server error), we don't want to return raw exception messages.
 * Instead, we return a CONSISTENT error format so API consumers
 * always know what to expect.
 *
 * WHY IS THIS IMPORTANT FOR CONTRACT TESTING?
 * Contract tests verify not just successful responses, but also
 * error responses. Having a consistent error format means our
 * contracts can reliably test error scenarios like:
 *   - POST /api/users with invalid email → 400 + ErrorResponse
 *   - GET /api/users/999 (not found) → 404 + ErrorResponse
 * ============================================================
 */
package com.contracttest.provider.model;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.Map;

/**
 * Standard error response returned by all API error cases.
 * This ensures consumers always receive a predictable error format.
 */
public class ErrorResponse {

    /**
     * HTTP status code (e.g., 400, 404, 500).
     * Duplicated here for convenience — consumers don't have to
     * parse HTTP headers to know the status.
     */
    private int status;

    /**
     * Human-readable error message explaining what went wrong.
     * Example: "User not found with id: 42"
     */
    private String message;

    /**
     * ISO-8601 timestamp of when the error occurred.
     * Example: "2026-03-13T10:30:00"
     * Useful for debugging and correlating with logs.
     */
    private String timestamp;

    /**
     * Field-level validation errors (only present for 400 Bad Request).
     * Key = field name, Value = validation error message.
     * Example: {"email": "Email must be a valid email address"}
     * Null when there are no field-specific errors.
     */
    private Map<String, String> fieldErrors;

    // ============================================================
    // CONSTRUCTORS
    // ============================================================

    /** No-arg constructor for Jackson deserialization. */
    public ErrorResponse() {
    }

    /**
     * Constructor for simple errors (no field-level details).
     * Automatically sets the timestamp to "now".
     *
     * @param status  HTTP status code
     * @param message Error description
     */
    public ErrorResponse(int status, String message) {
        this.status = status;
        this.message = message;
        this.timestamp = LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME);
    }

    /**
     * Constructor for validation errors with field-level details.
     *
     * @param status      HTTP status code (typically 400)
     * @param message     General error message
     * @param fieldErrors Map of field name → validation error message
     */
    public ErrorResponse(int status, String message, Map<String, String> fieldErrors) {
        this.status = status;
        this.message = message;
        this.timestamp = LocalDateTime.now().format(DateTimeFormatter.ISO_LOCAL_DATE_TIME);
        this.fieldErrors = fieldErrors;
    }

    // ============================================================
    // GETTERS AND SETTERS
    // ============================================================

    public int getStatus() {
        return status;
    }

    public void setStatus(int status) {
        this.status = status;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public String getTimestamp() {
        return timestamp;
    }

    public void setTimestamp(String timestamp) {
        this.timestamp = timestamp;
    }

    public Map<String, String> getFieldErrors() {
        return fieldErrors;
    }

    public void setFieldErrors(Map<String, String> fieldErrors) {
        this.fieldErrors = fieldErrors;
    }
}
