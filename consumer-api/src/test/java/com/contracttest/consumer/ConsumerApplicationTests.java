/*
 * ============================================================
 * ConsumerApplicationTests.java — Smoke Test
 * ============================================================
 * Same as Provider's test — verifies the Spring context loads
 * without errors. This catches configuration problems early.
 * ============================================================
 */
package com.contracttest.consumer;

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class ConsumerApplicationTests {

    @Test
    void contextLoads() {
        // If the Spring context loads successfully, this test passes.
    }
}
