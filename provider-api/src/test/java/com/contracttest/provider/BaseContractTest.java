/*
 * ============================================================
 * BaseContractTest.java — Foundation for Auto-Generated Tests
 * ============================================================
 * This is the BASE CLASS that all auto-generated contract tests
 * will extend. The SCC Maven plugin generates test classes, and
 * each one extends this class.
 *
 * WHY IS THIS NEEDED?
 * The auto-generated tests need a running API to test against.
 * This class sets up the Spring MVC context so the tests can
 * call your real controller endpoints WITHOUT starting a full
 * server (it uses MockMvc instead — faster and isolated).
 *
 * WHAT IS RestAssuredMockMvc?
 * It's a testing library that lets you make HTTP-like requests
 * to your controllers in-memory (no real HTTP). It's used by
 * the auto-generated contract tests to call your endpoints.
 *
 * WHAT HAPPENS DURING `mvn test`?
 * 1. SCC plugin reads YAML contracts
 * 2. SCC plugin generates test classes like:
 *      class UserTest extends BaseContractTest {
 *          @Test void should_return_user_by_id() { ... }
 *      }
 * 3. These tests use the setup from THIS class
 * 4. Tests run and verify the API matches the contracts
 * ============================================================
 */
package com.contracttest.provider;

import com.contracttest.provider.controller.UserController;
import com.contracttest.provider.service.UserService;
import io.restassured.module.mockmvc.RestAssuredMockMvc;
import org.junit.jupiter.api.BeforeEach;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

/**
 * @SpringBootTest loads the FULL application context.
 * This means UserService gets its @PostConstruct sample data,
 * and all beans are wired — just like the real running app.
 *
 * IMPORTANT: Data is RESET before each test so that tests are
 * independent. Without this, a DELETE test could remove a user
 * and break subsequent GET tests that expect that user to exist.
 */
@SpringBootTest
public abstract class BaseContractTest {

    @Autowired
    private UserController userController;

    @Autowired
    private UserService userService;

    /**
     * @BeforeEach runs before EACH auto-generated test method.
     *
     * Two things happen here:
     * 1. Reset the in-memory data store to its initial state (3 users)
     *    This ensures every test starts with clean, predictable data
     *    regardless of execution order.
     * 2. Configure RestAssuredMockMvc to use our UserController.
     *    This creates an in-memory MockMvc instance — no real HTTP needed.
     */
    @BeforeEach
    public void setup() {
        userService.resetData();
        RestAssuredMockMvc.standaloneSetup(userController);
    }
}
