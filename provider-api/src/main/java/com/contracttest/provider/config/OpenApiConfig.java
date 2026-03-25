/*
 * ============================================================
 * OpenApiConfig.java — OpenAPI/Swagger Configuration
 * ============================================================
 * This class customizes the auto-generated OpenAPI documentation.
 * springdoc-openapi reads this configuration to create a rich,
 * descriptive API specification document.
 *
 * WHY IS THIS IMPORTANT FOR OUR PROJECT?
 * The OpenAPI spec generated here is the "single source of truth"
 * that our AI Agent will read to auto-generate contract files.
 * The richer and more accurate this spec is, the better contracts
 * the AI Agent can generate.
 *
 * WHAT IS OpenAPI?
 * OpenAPI (formerly Swagger) is a STANDARD FORMAT for describing
 * REST APIs. It's a JSON/YAML file that lists all endpoints,
 * request/response formats, status codes, etc.
 * ============================================================
 */
package com.contracttest.provider.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.License;
import io.swagger.v3.oas.models.servers.Server;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.List;

/**
 * @Configuration tells Spring: "This class contains bean definitions."
 * A "bean" is an object that Spring creates and manages for you.
 */
@Configuration
public class OpenApiConfig {

    /**
     * Defines a custom OpenAPI specification with project metadata.
     *
     * @Bean tells Spring: "Create this object and manage it."
     * The returned OpenAPI object customizes the generated spec.
     *
     * @return Configured OpenAPI specification object
     */
    @Bean
    public OpenAPI customOpenAPI() {
        return new OpenAPI()
                // --- API Metadata ---
                .info(new Info()
                        .title("User Management API")
                        .version("1.0.0")
                        .description("""
                                REST API for managing users. This API serves as the
                                Provider in our contract testing setup. The OpenAPI
                                specification generated from this API is used by the
                                AI Agent to auto-generate Spring Cloud Contract files.
                                """)
                        .contact(new Contact()
                                .name("Contract Testing Team")
                                .email("team@contracttest.com"))
                        .license(new License()
                                .name("MIT License")
                                .url("https://opensource.org/licenses/MIT")))
                // --- Server Definitions ---
                // These tell API consumers where to reach the API
                .servers(List.of(
                        new Server()
                                .url("http://localhost:8080")
                                .description("Local Development Server"),
                        new Server()
                                .url("http://localhost:8081")
                                .description("Contract Test Server")
                ));
    }
}
