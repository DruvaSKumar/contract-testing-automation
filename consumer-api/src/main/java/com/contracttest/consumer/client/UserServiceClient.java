/*
 * ============================================================
 * UserServiceClient.java — HTTP Client for the Provider API
 * ============================================================
 * THIS IS THE HEART OF THE CONSUMER-PROVIDER RELATIONSHIP.
 *
 * This class makes HTTP calls to the Provider (User Service)
 * API to fetch user data. It's what makes us a "consumer."
 *
 * HOW IT WORKS:
 *   1. Order Service needs user data for an order
 *   2. It calls UserServiceClient.getUserById(userId)
 *   3. UserServiceClient sends HTTP GET to Provider:
 *      http://localhost:8080/api/users/{userId}
 *   4. Provider responds with JSON: {id, name, email, role}
 *   5. RestTemplate converts JSON → UserDTO object
 *   6. Order Service uses this UserDTO to build OrderResponse
 *
 * WHAT IS RestTemplate?
 * RestTemplate is Spring's built-in HTTP client for making
 * REST API calls. It handles:
 *   - Building HTTP requests (method, URL, headers)
 *   - Sending the request over the network
 *   - Reading the response and converting JSON to Java objects
 * Think of it as "Postman in code" — it calls APIs for you.
 *
 * WHY THIS CLASS EXISTS (for contract testing):
 * This is the exact point where things can break. If the
 * Provider changes its response format, RestTemplate will
 * either get wrong data or throw an error. Contract tests
 * ensure the Provider always returns what we expect here.
 * ============================================================
 */
package com.contracttest.consumer.client;

import com.contracttest.consumer.model.UserDTO;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

/**
 * Client that calls the Provider (User Service) API.
 *
 * @Component tells Spring to create and manage this bean.
 * Other classes can then get it via constructor injection.
 */
@Component
public class UserServiceClient {

    private static final Logger log = LoggerFactory.getLogger(UserServiceClient.class);

    /**
     * Spring's HTTP client — we use it to call the Provider API.
     * It's configured as a bean in RestTemplateConfig.java.
     */
    private final RestTemplate restTemplate;

    /**
     * Base URL of the Provider API.
     *
     * @Value reads from application.yml:
     *   provider:
     *     api:
     *       base-url: http://localhost:8080
     *
     * This lets us change the URL without modifying code.
     */
    private final String providerBaseUrl;

    /**
     * Constructor injection — Spring provides RestTemplate and
     * reads the provider URL from application.yml.
     */
    public UserServiceClient(
            RestTemplate restTemplate,
            @Value("${provider.api.base-url}") String providerBaseUrl) {
        this.restTemplate = restTemplate;
        this.providerBaseUrl = providerBaseUrl;
    }

    /**
     * Fetch a user from the Provider API by their ID.
     *
     * THIS IS THE CRITICAL INTER-SERVICE CALL:
     *   - We call: GET http://localhost:8080/api/users/{id}
     *   - We expect: {id: 1, name: "Alice", email: "...", role: "ADMIN"}
     *   - RestTemplate converts the JSON response into a UserDTO
     *
     * If the Provider changes any of these fields, this breaks.
     * CONTRACT TESTS prevent this from happening.
     *
     * @param userId The ID of the user to fetch
     * @return UserDTO with user data, or null if not found / error
     */
    public UserDTO getUserById(Long userId) {
        String url = providerBaseUrl + "/api/users/" + userId;
        log.debug("Calling Provider API: GET {}", url);

        try {
            /*
             * restTemplate.getForObject(url, UserDTO.class):
             *   1. Sends HTTP GET to the URL
             *   2. Reads the JSON response body
             *   3. Converts it to a UserDTO object using Jackson
             *
             * If the Provider is running and user exists → returns UserDTO
             * If user doesn't exist → Provider returns 404 → exception
             * If Provider is down → connection refused → exception
             */
            UserDTO user = restTemplate.getForObject(url, UserDTO.class);
            log.debug("Received user from Provider: {}", user);
            return user;

        } catch (HttpClientErrorException.NotFound e) {
            // Provider returned 404 — user doesn't exist
            log.warn("User not found at Provider: userId={}", userId);
            return null;

        } catch (RestClientException e) {
            // Network error, Provider is down, timeout, etc.
            log.error("Failed to call Provider API: {}", e.getMessage());
            return null;
        }
    }
}
