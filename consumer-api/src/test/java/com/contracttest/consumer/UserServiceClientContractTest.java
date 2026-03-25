/*
 * ============================================================
 * UserServiceClientContractTest.java — Consumer Contract Test
 * ============================================================
 * This tests our Consumer's UserServiceClient AGAINST STUBS
 * generated from the Provider's contracts.
 *
 * HOW IT WORKS:
 * 1. Provider runs `mvn install` → generates stubs JAR
 * 2. Stubs JAR contains WireMock mappings (fake responses)
 * 3. @AutoConfigureStubRunner starts a WireMock server
 * 4. WireMock serves fake responses matching the contracts
 * 5. Our UserServiceClient calls WireMock instead of real Provider
 * 6. We verify our client correctly parses the responses
 *
 * WHY IS THIS IMPORTANT?
 * - We can test the Consumer WITHOUT the real Provider running
 * - The fake responses are GUARANTEED to match what the real
 *   Provider produces (because both come from the same contracts)
 * - If someone changes a contract, both Provider and Consumer
 *   tests must be updated — keeping them in sync
 *
 * @AutoConfigureStubRunner:
 *   - ids: "groupId:artifactId:+:stubs:port"
 *     → Finds stubs for provider-api, latest version, on port 8080
 *   - stubsMode = LOCAL: Look for stubs in local Maven repo
 *     (the Provider must have run `mvn install` first)
 * ============================================================
 */
package com.contracttest.consumer;

import com.contracttest.consumer.client.UserServiceClient;
import com.contracttest.consumer.model.UserDTO;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.cloud.contract.stubrunner.spring.AutoConfigureStubRunner;
import org.springframework.cloud.contract.stubrunner.spring.StubRunnerProperties;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@AutoConfigureStubRunner(
        /*
         * ids format: "groupId:artifactId:version:classifier:port"
         *   - com.contracttest:provider-api → matches the Provider's pom.xml coordinates
         *   - + → use the latest version of stubs available
         *   - stubs → the classifier for the stubs JAR
         *   - 8080 → run the WireMock stub server on port 8080
         *            (same port our UserServiceClient expects)
         */
        ids = "com.contracttest:provider-api:+:stubs:8080",
        /*
         * LOCAL mode: Look for stubs in the local Maven repository
         * (~/.m2/repository). The Provider must run `mvn install`
         * first to generate and store the stubs there.
         */
        stubsMode = StubRunnerProperties.StubsMode.LOCAL
)
class UserServiceClientContractTest {

    @Autowired
    private UserServiceClient userServiceClient;

    /**
     * Test: Our client can correctly call GET /api/users/1
     * and parse the response into a UserDTO.
     *
     * The WireMock stub server (started by @AutoConfigureStubRunner)
     * responds with the exact response defined in the contract:
     *   should_return_user_by_id.yml
     *
     * This proves our Consumer correctly understands the Provider's API.
     */
    @Test
    void shouldGetUserById() {
        // Call our client — it thinks it's calling the real Provider,
        // but it's actually calling the WireMock stub server
        UserDTO user = userServiceClient.getUserById(1L);

        // Verify the response was correctly parsed
        assertThat(user).isNotNull();
        assertThat(user.getId()).isEqualTo(1L);
        assertThat(user.getName()).isNotBlank();
        assertThat(user.getEmail()).contains("@");
        assertThat(user.getRole()).isNotBlank();
    }
}
