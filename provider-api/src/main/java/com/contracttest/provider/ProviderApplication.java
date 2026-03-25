/*
 * ============================================================
 * ProviderApplication.java — Main Entry Point
 * ============================================================
 * This is the STARTING POINT of our Spring Boot application.
 * When you run this class, it:
 *   1. Starts an embedded Tomcat web server
 *   2. Scans for all Spring components (@Controller, @Service, etc.)
 *   3. Configures everything automatically (auto-configuration)
 *   4. Makes the REST API available at http://localhost:8080
 *
 * WHAT IS @SpringBootApplication?
 * It's a shortcut that combines 3 annotations:
 *   - @Configuration: This class can define beans (objects managed by Spring)
 *   - @EnableAutoConfiguration: Spring Boot auto-configures based on dependencies
 *   - @ComponentScan: Scans this package and sub-packages for Spring components
 * ============================================================
 */
package com.contracttest.provider;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class ProviderApplication {

    /**
     * The main method — Java's universal entry point.
     * SpringApplication.run() bootstraps the entire Spring Boot application.
     *
     * @param args Command-line arguments (e.g., --server.port=9090)
     */
    public static void main(String[] args) {
        SpringApplication.run(ProviderApplication.class, args);
    }
}
