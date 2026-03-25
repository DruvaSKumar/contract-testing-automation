/*
 * ============================================================
 * OrderResponse.java — Enriched Order Response with User Data
 * ============================================================
 * When a client asks for an order, they want to see not just
 * the userId, but the actual user's name, email, etc.
 *
 * This class combines:
 *   - Order data (from our own Order Service)
 *   - User data (fetched from the Provider's User Service)
 *
 * THIS IS WHERE THE INTER-SERVICE DEPENDENCY HAPPENS:
 *   1. Client requests: GET /api/orders/1
 *   2. Order Service finds order #1 (userId = 2)
 *   3. Order Service calls Provider: GET /api/users/2
 *   4. Provider returns: {id:2, name:"Bob Smith", ...}
 *   5. Order Service combines both into OrderResponse
 *   6. Client receives the enriched response
 *
 * If the Provider's User API changes its response format,
 * step 4 breaks, and the client gets wrong/missing data.
 * Contract tests ensure step 4 always works as expected.
 * ============================================================
 */
package com.contracttest.consumer.model;

/**
 * Response DTO that combines Order details with User information.
 * This is what the API returns to its clients.
 */
public class OrderResponse {

    // --- Order fields ---
    private Long id;
    private String productName;
    private Integer quantity;
    private Double price;
    private String status;

    // --- User fields (fetched from Provider API) ---

    /** The user ID (same as stored in the Order) */
    private Long userId;

    /** User's name (fetched from Provider — THIS IS THE CONTRACT DEPENDENCY) */
    private String userName;

    /** User's email (fetched from Provider — THIS IS THE CONTRACT DEPENDENCY) */
    private String userEmail;

    // --- Constructors ---

    public OrderResponse() {
    }

    /**
     * Creates an OrderResponse by combining an Order with User data.
     * This is the key method — it merges data from TWO services.
     *
     * @param order The order from our local store
     * @param user  The user fetched from the Provider API (can be null if Provider is down)
     */
    public OrderResponse(Order order, UserDTO user) {
        this.id = order.getId();
        this.productName = order.getProductName();
        this.quantity = order.getQuantity();
        this.price = order.getPrice();
        this.status = order.getStatus();
        this.userId = order.getUserId();

        // If we successfully got user data from the Provider, include it
        if (user != null) {
            this.userName = user.getName();
            this.userEmail = user.getEmail();
        } else {
            // Provider might be down or user might not exist
            this.userName = "Unknown (User Service unavailable)";
            this.userEmail = "N/A";
        }
    }

    // --- Getters and Setters ---

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getProductName() {
        return productName;
    }

    public void setProductName(String productName) {
        this.productName = productName;
    }

    public Integer getQuantity() {
        return quantity;
    }

    public void setQuantity(Integer quantity) {
        this.quantity = quantity;
    }

    public Double getPrice() {
        return price;
    }

    public void setPrice(Double price) {
        this.price = price;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public Long getUserId() {
        return userId;
    }

    public void setUserId(Long userId) {
        this.userId = userId;
    }

    public String getUserName() {
        return userName;
    }

    public void setUserName(String userName) {
        this.userName = userName;
    }

    public String getUserEmail() {
        return userEmail;
    }

    public void setUserEmail(String userEmail) {
        this.userEmail = userEmail;
    }
}
