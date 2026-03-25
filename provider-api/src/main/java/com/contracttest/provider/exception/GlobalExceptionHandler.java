/*
 * ============================================================
 * GlobalExceptionHandler.java — Centralized Error Handling
 * ============================================================
 * This class catches exceptions thrown by ANY controller and
 * converts them into consistent ErrorResponse objects.
 *
 * WITHOUT THIS: Spring would return its default error format
 * (a "Whitelabel Error Page" or generic JSON), which varies
 * and is hard to test against in contracts.
 *
 * WITH THIS: Every error returns our standardized ErrorResponse
 * format, making contract testing predictable and reliable.
 *
 * WHAT IS @RestControllerAdvice?
 * It's a global exception handler that applies to ALL controllers.
 * It combines:
 *   - @ControllerAdvice: "Apply this to all controllers"
 *   - @ResponseBody: "Return values as JSON, not HTML"
 *
 * WHAT IS @ExceptionHandler?
 * Marks a method as a handler for a SPECIFIC exception type.
 * When that exception is thrown anywhere in the app, Spring
 * calls this method instead of returning a generic error.
 * ============================================================
 */
package com.contracttest.provider.exception;

import com.contracttest.provider.model.ErrorResponse;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

import java.util.HashMap;
import java.util.Map;

@RestControllerAdvice
public class GlobalExceptionHandler {

    /**
     * Handles VALIDATION errors (400 Bad Request).
     *
     * WHEN DOES THIS TRIGGER?
     * When @Valid on a @RequestBody fails — e.g., a POST /api/users
     * with blank name or invalid email. Spring throws
     * MethodArgumentNotValidException, and this method catches it.
     *
     * WHAT DOES IT DO?
     * Extracts each field's error message and puts them in a map:
     *   {"name": "Name is required", "email": "must be a valid email"}
     * This gives API consumers specific, actionable error details.
     *
     * @param ex The exception containing validation error details
     * @return 400 response with field-level error details
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidationErrors(
            MethodArgumentNotValidException ex) {

        // Build a map of field name → error message
        Map<String, String> fieldErrors = new HashMap<>();
        ex.getBindingResult().getFieldErrors().forEach(error ->
                fieldErrors.put(
                        error.getField(),           // e.g., "email"
                        error.getDefaultMessage()   // e.g., "must be a valid email"
                )
        );

        ErrorResponse errorResponse = new ErrorResponse(
                HttpStatus.BAD_REQUEST.value(),    // 400
                "Validation failed: please check the field errors for details",
                fieldErrors
        );

        return ResponseEntity.badRequest().body(errorResponse);
    }

    /**
     * Handles ALL other unexpected exceptions (500 Internal Server Error).
     *
     * This is a SAFETY NET. If any unhandled exception occurs
     * (bug, null pointer, etc.), this catches it and returns a
     * clean error response instead of an ugly stack trace.
     *
     * @param ex The unexpected exception
     * @return 500 response with a generic error message
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleGenericException(Exception ex) {
        ErrorResponse errorResponse = new ErrorResponse(
                HttpStatus.INTERNAL_SERVER_ERROR.value(),  // 500
                "An unexpected error occurred"
                // Note: We do NOT expose ex.getMessage() to the client
                // for security reasons — it might contain sensitive info.
                // The message is logged server-side for debugging.
        );

        return ResponseEntity
                .status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(errorResponse);
    }
}
