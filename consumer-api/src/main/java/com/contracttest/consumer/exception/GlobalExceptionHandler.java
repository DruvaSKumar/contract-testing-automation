/*
 * ============================================================
 * GlobalExceptionHandler.java — Centralized Error Handling
 * ============================================================
 * Same pattern as the Provider's GlobalExceptionHandler.
 * Catches validation errors (400) and unexpected errors (500),
 * returning consistent ErrorResponse objects.
 * ============================================================
 */
package com.contracttest.consumer.exception;

import com.contracttest.consumer.model.ErrorResponse;
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
     * Handles validation errors (400 Bad Request).
     * Triggered when @Valid fails on a @RequestBody.
     */
    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidationErrors(
            MethodArgumentNotValidException ex) {

        Map<String, String> fieldErrors = new HashMap<>();
        ex.getBindingResult().getFieldErrors().forEach(error ->
                fieldErrors.put(error.getField(), error.getDefaultMessage())
        );

        ErrorResponse errorResponse = new ErrorResponse(
                HttpStatus.BAD_REQUEST.value(),
                "Validation failed: please check the field errors for details",
                fieldErrors
        );

        return ResponseEntity.badRequest().body(errorResponse);
    }

    /**
     * Handles all other unexpected exceptions (500 Internal Server Error).
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleGenericException(Exception ex) {
        ErrorResponse errorResponse = new ErrorResponse(
                HttpStatus.INTERNAL_SERVER_ERROR.value(),
                "An unexpected error occurred"
        );
        return ResponseEntity
                .status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(errorResponse);
    }
}
