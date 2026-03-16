/*
 * ============================================================
 * RestTemplateConfig.java — HTTP Client Configuration
 * ============================================================
 * This configures RestTemplate — Spring's HTTP client that our
 * Order Service uses to call the Provider (User Service) API.
 *
 * WHY IS THIS A SEPARATE CONFIG CLASS?
 * RestTemplate needs to be a Spring-managed @Bean so that:
 *   1. Spring creates ONE instance and reuses it (efficient)
 *   2. It can be injected into any class that needs it
 *   3. It can be EASILY REPLACED with a mock in tests
 *      (this is important for contract testing in Phase 2!)
 *
 * WHAT IS RestTemplate?
 * Think of it as "Postman inside your Java code."
 * It can make HTTP GET, POST, PUT, DELETE requests to other
 * services and automatically convert JSON responses to Java objects.
 *
 * Example:
 *   UserDTO user = restTemplate.getForObject(
 *       "http://localhost:8080/api/users/1",
 *       UserDTO.class
 *   );
 *   // user.getName() → "Alice Johnson"
 * ============================================================
 */
package com.contracttest.consumer.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestTemplate;

@Configuration
public class RestTemplateConfig {

    /**
     * Creates a RestTemplate bean that Spring manages.
     *
     * @Bean tells Spring: "Create this object once and reuse it."
     * Any class that needs RestTemplate can get it via:
     *   - Constructor injection (recommended)
     *   - @Autowired (older style)
     *
     * @return A configured RestTemplate instance
     */
    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }
}
