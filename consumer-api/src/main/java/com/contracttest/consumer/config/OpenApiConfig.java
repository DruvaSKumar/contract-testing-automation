/*
 * ============================================================
 * OpenApiConfig.java — OpenAPI Documentation Configuration
 * ============================================================
 * Same pattern as Provider's OpenApiConfig but describes
 * the Consumer (Order Service) API.
 * ============================================================
 */
package com.contracttest.consumer.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.servers.Server;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.List;

@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI customOpenAPI() {
        return new OpenAPI()
                .info(new Info()
                        .title("Order Management API (Consumer)")
                        .version("1.0.0")
                        .description("""
                                REST API for managing orders. This is the CONSUMER
                                service that depends on the Provider (User Service)
                                API. Order responses include user data fetched from
                                the Provider, demonstrating the inter-service
                                dependency that contract testing protects.
                                """)
                        .contact(new Contact()
                                .name("Contract Testing Team")
                                .email("team@contracttest.com")))
                .servers(List.of(
                        new Server()
                                .url("http://localhost:8081")
                                .description("Consumer API - Local Development")));
    }
}
