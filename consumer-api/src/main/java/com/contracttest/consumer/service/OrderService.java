/*
 * ============================================================
 * OrderService.java — Business Logic Layer (Order Service)
 * ============================================================
 * This is the business logic for our Order Service.
 * Same pattern as the Provider's UserService:
 *   - In-memory storage (ConcurrentHashMap)
 *   - CRUD operations
 *   - Pre-loaded sample data
 *
 * THE KEY DIFFERENCE FROM PROVIDER'S SERVICE:
 * This service CALLS another service (the Provider/User Service)
 * to enrich its responses with user data. It uses the
 * UserServiceClient to make those HTTP calls.
 *
 * DATA FLOW FOR GET /api/orders/{id}:
 *   1. Controller calls orderService.getOrderById(id)
 *   2. OrderService finds the Order in its local store
 *   3. OrderService sees the order has userId = 2
 *   4. OrderService calls userServiceClient.getUserById(2)
 *   5. UserServiceClient calls Provider: GET localhost:8080/api/users/2
 *   6. Provider returns: {id:2, name:"Bob Smith", ...}
 *   7. OrderService combines Order + User → OrderResponse
 *   8. Controller returns the enriched OrderResponse
 * ============================================================
 */
package com.contracttest.consumer.service;

import com.contracttest.consumer.client.UserServiceClient;
import com.contracttest.consumer.model.Order;
import com.contracttest.consumer.model.OrderResponse;
import com.contracttest.consumer.model.UserDTO;
import jakarta.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

@Service
public class OrderService {

    private static final Logger log = LoggerFactory.getLogger(OrderService.class);

    /** In-memory order store — same pattern as Provider's userStore */
    private final Map<Long, Order> orderStore = new ConcurrentHashMap<>();

    /** Thread-safe ID counter — same pattern as Provider */
    private final AtomicLong idCounter = new AtomicLong(1);

    /**
     * The HTTP client that calls the Provider (User Service) API.
     * This is the INTER-SERVICE dependency.
     */
    private final UserServiceClient userServiceClient;

    /**
     * Constructor injection — Spring provides the UserServiceClient.
     */
    public OrderService(UserServiceClient userServiceClient) {
        this.userServiceClient = userServiceClient;
    }

    /**
     * Pre-populate with sample orders on startup.
     * Notice: userId values reference users in the PROVIDER API:
     *   - userId 1 → Alice Johnson (ADMIN) in Provider
     *   - userId 2 → Bob Smith (USER) in Provider
     *   - userId 3 → Charlie Brown (MANAGER) in Provider
     */
    @PostConstruct
    public void initSampleData() {
        createOrder(new Order(null, "Laptop Pro 16", 1, 1299.99, 1L, "CONFIRMED"));
        createOrder(new Order(null, "Wireless Mouse", 2, 29.99, 2L, "PENDING"));
        createOrder(new Order(null, "USB-C Monitor", 1, 449.99, 1L, "SHIPPED"));
        createOrder(new Order(null, "Mechanical Keyboard", 1, 149.99, 3L, "PENDING"));
    }

    /**
     * Get ALL orders with enriched user data.
     * For each order, we call the Provider API to get user details.
     *
     * @return List of OrderResponse (order + user data combined)
     */
    public List<OrderResponse> getAllOrders() {
        return orderStore.values().stream()
                .map(this::enrichOrderWithUserData)
                .toList();
    }

    /**
     * Get a SINGLE order by ID with enriched user data.
     *
     * @param id The order's unique identifier
     * @return Optional containing enriched OrderResponse if found
     */
    public Optional<OrderResponse> getOrderById(Long id) {
        return Optional.ofNullable(orderStore.get(id))
                .map(this::enrichOrderWithUserData);
    }

    /**
     * Create a new order.
     * Returns the enriched response (with user data from Provider).
     *
     * @param order The order data from the request body
     * @return OrderResponse with order + user data
     */
    public OrderResponse createOrder(Order order) {
        Long newId = idCounter.getAndIncrement();
        order.setId(newId);

        // If no status provided, default to PENDING
        if (order.getStatus() == null) {
            order.setStatus("PENDING");
        }

        orderStore.put(newId, order);
        log.debug("Created order #{} for userId {}", newId, order.getUserId());

        return enrichOrderWithUserData(order);
    }

    /**
     * Delete an order by ID.
     *
     * @param id The order ID to delete
     * @return true if found and deleted, false if not found
     */
    public boolean deleteOrder(Long id) {
        return orderStore.remove(id) != null;
    }

    /**
     * THE CRITICAL METHOD — Enriches an Order with User data.
     *
     * This is where the INTER-SERVICE CALL happens:
     *   1. Takes an Order (which has only userId)
     *   2. Calls the Provider API to get the full User data
     *   3. Combines them into an OrderResponse
     *
     * If the Provider API changes its response format (e.g.,
     * renames "name" to "fullName"), the UserDTO won't get the
     * name field, and userName in the response will be null.
     * CONTRACT TESTS prevent this scenario.
     */
    private OrderResponse enrichOrderWithUserData(Order order) {
        // Call Provider API to get user data
        UserDTO user = userServiceClient.getUserById(order.getUserId());

        // Combine order + user into a single response
        // If user is null (Provider down or user not found),
        // OrderResponse handles it gracefully
        return new OrderResponse(order, user);
    }
}
