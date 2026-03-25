/*
 * ============================================================
 * ProviderApplicationTests.java — Basic Application Test
 * ============================================================
 * This is a SMOKE TEST — it verifies that the application
 * can start up without errors. If any configuration is wrong,
 * beans can't be created, or dependencies are missing, this
 * test will fail.
 *
 * WHAT IS @SpringBootTest?
 * It loads the FULL Spring application context (all beans,
 * all configurations) just like when you run the app normally.
 * This is an integration test — it tests that everything
 * wires together correctly.
 *
 * WHY IS THIS IMPORTANT?
 * It catches configuration errors, missing dependencies, and
 * circular bean references EARLY — before you deploy.
 * ============================================================
 */
package com.contracttest.provider;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class ProviderApplicationTests {

    /**
     * Verifies that the Spring application context loads successfully.
     * If this test passes, it means:
     *   - All beans are created without errors
     *   - All dependencies are satisfied
     *   - Configuration is valid
     *
     * If this test fails, check the error log for details about
     * which bean or configuration caused the failure.
     */
    @Test
    void contextLoads() {
        // No assertions needed — if the context loads, the test passes.
        // Spring Boot will throw an exception if anything is misconfigured.
    }
}
