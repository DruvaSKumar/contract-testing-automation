/*
 * ============================================================
 * Order.java — Order Data Model
 * ============================================================
 * This class represents an ORDER in our system. It stores:
 *   - Order details (product, quantity, price, status)
 *   - A userId reference (which user placed this order)
 *
 * NOTICE: We store userId (a number), NOT the full User object.
 * This is standard microservice practice:
 *   - The Order Service stores only the user's ID
 *   - When it needs full user details, it CALLS the User Service
 *   - This keeps services loosely coupled (independent)
 *
 * Think of it like a database foreign key — you store the ID,
 * and look up the details when needed.
 * ============================================================
 */
package com.contracttest.consumer.model;

import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;

public class Order {

    /** Unique identifier for the order (auto-generated) */
    private Long id;

    /**
     * The name of the product being ordered.
     * @NotBlank: Must not be null or empty.
     */
    @NotBlank(message = "Product name is required and cannot be blank")
    private String productName;

    /**
     * How many units of the product are ordered.
     * @NotNull: Must be provided (can't be null).
     * @Min(1): Must order at least 1 item.
     */
    @NotNull(message = "Quantity is required")
    @Min(value = 1, message = "Quantity must be at least 1")
    private Integer quantity;

    /**
     * Price per unit (in dollars).
     * @NotNull: Must be provided.
     * @DecimalMin("0.01"): Must be a positive price.
     */
    @NotNull(message = "Price is required")
    @DecimalMin(value = "0.01", message = "Price must be greater than 0")
    private Double price;

    /**
     * ID of the user who placed this order.
     * This references a User in the Provider (User Service).
     * We DON'T store the full user data — we fetch it when needed.
     *
     * @NotNull: Every order must belong to a user.
     */
    @NotNull(message = "User ID is required")
    private Long userId;

    /**
     * Current status of the order.
     * Examples: "PENDING", "CONFIRMED", "SHIPPED", "DELIVERED"
     */
    private String status;

    // --- Constructors ---

    public Order() {
    }

    public Order(Long id, String productName, Integer quantity, Double price, Long userId, String status) {
        this.id = id;
        this.productName = productName;
        this.quantity = quantity;
        this.price = price;
        this.userId = userId;
        this.status = status;
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

    public Long getUserId() {
        return userId;
    }

    public void setUserId(Long userId) {
        this.userId = userId;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    @Override
    public String toString() {
        return "Order{id=" + id + ", productName='" + productName + "', quantity=" + quantity
                + ", price=" + price + ", userId=" + userId + ", status='" + status + "'}";
    }
}
