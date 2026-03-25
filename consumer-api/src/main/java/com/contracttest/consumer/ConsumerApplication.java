/*
 * ============================================================
 * ConsumerApplication.java — Main Entry Point (Order Service)
 * ============================================================
 * This is the STARTING POINT of our Consumer API (Order Service).
 * It works exactly like the Provider's ProviderApplication.java:
 *   1. Starts an embedded Tomcat web server
 *   2. Scans for all Spring components
 *   3. Makes the REST API available
 *
 * KEY DIFFERENCE: This runs on port 8081 (not 8080).
 * Why? Because we need BOTH services running simultaneously:
 *   - Provider (User Service) → http://localhost:8080
 *   - Consumer (Order Service) → http://localhost:8081
 *
 * Two services can't use the same port on the same machine.
 * ============================================================
 */
package com.contracttest.consumer;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class ConsumerApplication {

    public static void main(String[] args) {
        SpringApplication.run(ConsumerApplication.class, args);
    }
}
