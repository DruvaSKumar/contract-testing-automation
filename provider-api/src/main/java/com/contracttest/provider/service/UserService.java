/*
 * ============================================================
 * UserService.java — Business Logic Layer
 * ============================================================
 * This class contains all the BUSINESS LOGIC for user operations.
 * It sits between the Controller (HTTP layer) and the data store.
 *
 * WHY SEPARATE SERVICE FROM CONTROLLER?
 * Separation of concerns — a core software engineering principle:
 *   - Controller: Handles HTTP requests/responses (web layer)
 *   - Service: Contains business logic (what to DO with the data)
 *   - Repository/Store: Manages data persistence (where to STORE data)
 *
 * This makes the code easier to test, maintain, and modify.
 * You can change how data is stored (e.g., switch from in-memory
 * to a database) without changing the controller or business logic.
 *
 * DATA STORAGE:
 * For this project, we use an IN-MEMORY HashMap instead of a
 * database. This keeps the project simple and focused on contract
 * testing (not database setup). The data resets when the app restarts.
 *
 * WHAT IS @Service?
 * It tells Spring: "This class is a service bean — create one
 * instance and manage it." Other classes can then use @Autowired
 * to get a reference to this service.
 * ============================================================
 */
package com.contracttest.provider.service;

import com.contracttest.provider.model.User;
import jakarta.annotation.PostConstruct;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

@Service
public class UserService {

    /**
     * In-memory data store using ConcurrentHashMap.
     *
     * WHY ConcurrentHashMap instead of HashMap?
     * ConcurrentHashMap is THREAD-SAFE — it can handle multiple
     * requests accessing the data simultaneously without corruption.
     * A web server handles many requests in parallel, so thread
     * safety is important even for a demo project.
     *
     * Key = User ID (Long), Value = User object
     */
    private final Map<Long, User> userStore = new ConcurrentHashMap<>();

    /**
     * Atomic counter for generating unique user IDs.
     *
     * WHY AtomicLong instead of a regular long?
     * AtomicLong is thread-safe — if two requests try to create
     * users simultaneously, they'll each get a UNIQUE ID guaranteed.
     * A regular long++ could give duplicate IDs under concurrency.
     */
    private final AtomicLong idCounter = new AtomicLong(1);

    /**
     * @PostConstruct runs ONCE after the bean is created.
     * We use it to pre-populate the store with sample data
     * so the API has data to work with immediately.
     *
     * These sample users also serve as expected data in our
     * contract tests — contracts can verify these users exist.
     */
    @PostConstruct
    public void initSampleData() {
        createUser(new User(null, "Alice Johnson", "alice@example.com", "ADMIN"));
        createUser(new User(null, "Bob Smith", "bob@example.com", "USER"));
        createUser(new User(null, "Charlie Brown", "charlie@example.com", "MANAGER"));
    }

    /**
     * Retrieve ALL users from the store.
     *
     * @return List of all users (may be empty, never null)
     */
    public List<User> getAllUsers() {
        // Convert the Map's values (Collection<User>) to a List<User>
        return new ArrayList<>(userStore.values());
    }

    /**
     * Retrieve a SINGLE user by their ID.
     *
     * WHY Optional<User> instead of User?
     * Optional is Java's way of saying "this might or might not
     * have a value." It forces the caller to handle the "not found"
     * case explicitly, preventing NullPointerException bugs.
     *
     * @param id The user's unique identifier
     * @return Optional containing the user if found, empty if not
     */
    public Optional<User> getUserById(Long id) {
        return Optional.ofNullable(userStore.get(id));
    }

    /**
     * Create a NEW user.
     * Assigns a unique auto-generated ID to the user.
     *
     * @param user The user data (id field is ignored, auto-assigned)
     * @return The created user with their assigned ID
     */
    public User createUser(User user) {
        // getAndIncrement() atomically returns current value and increments
        // First call returns 1, second returns 2, etc.
        Long newId = idCounter.getAndIncrement();
        user.setId(newId);
        userStore.put(newId, user);
        return user;
    }

    /**
     * UPDATE an existing user's data.
     * The user must already exist (identified by ID).
     *
     * @param id          The ID of the user to update
     * @param updatedUser The new data to apply
     * @return Optional containing the updated user if found, empty if not
     */
    public Optional<User> updateUser(Long id, User updatedUser) {
        // Check if the user exists before updating
        if (!userStore.containsKey(id)) {
            return Optional.empty();
        }
        updatedUser.setId(id); // Ensure the ID stays the same
        userStore.put(id, updatedUser);
        return Optional.of(updatedUser);
    }

    /**
     * DELETE a user by their ID.
     *
     * @param id The ID of the user to delete
     * @return true if the user was found and deleted, false if not found
     */
    public boolean deleteUser(Long id) {
        // remove() returns the removed value, or null if key wasn't found
        return userStore.remove(id) != null;
    }

    /**
     * Reset the data store to its initial state.
     *
     * WHY IS THIS NEEDED?
     * During contract testing, each test modifies shared in-memory data.
     * For example, a DELETE test removes a user, which would break
     * subsequent GET tests expecting that user to exist.
     *
     * By resetting before each test, we ensure every test starts
     * with the same 3 sample users — making tests independent and
     * repeatable regardless of execution order.
     */
    public void resetData() {
        userStore.clear();
        idCounter.set(1);
        initSampleData();
    }
}
