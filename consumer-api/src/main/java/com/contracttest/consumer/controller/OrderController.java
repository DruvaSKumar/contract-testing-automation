/*
 * ============================================================
 * OrderController.java — REST API Controller (Order Service)
 * ============================================================
 * HTTP layer for the Order Service. Same pattern as the
 * Provider's UserController, but with fewer endpoints since
 * Orders are simpler for this demo.
 *
 * ENDPOINTS:
 *   GET    /api/orders          → List all orders (with user data)
 *   GET    /api/orders/{id}     → Get a specific order (with user data)
 *   POST   /api/orders          → Create a new order
 *   DELETE /api/orders/{id}     → Delete an order
 *
 * KEY POINT:
 * Every GET response includes user data fetched from the Provider.
 * When you call GET /api/orders/1, the response includes:
 *   - Order info: productName, quantity, price, status
 *   - User info: userName, userEmail (fetched from Provider API)
 * ============================================================
 */
package com.contracttest.consumer.controller;

import com.contracttest.consumer.model.ErrorResponse;
import com.contracttest.consumer.model.OrderResponse;
import com.contracttest.consumer.model.Order;
import com.contracttest.consumer.service.OrderService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.ArraySchema;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/orders")
@Tag(name = "Order Management", description = "CRUD operations for managing orders. Order responses include user data fetched from the Provider (User Service).")
public class OrderController {

    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    // ============================================================
    // GET /api/orders — List all orders (with user data)
    // ============================================================

    @Operation(
            summary = "Get all orders",
            description = "Retrieves all orders with enriched user data. For each order, the service calls the Provider (User Service) to fetch the user's name and email."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "Successfully retrieved list of orders",
                    content = @Content(
                            mediaType = "application/json",
                            array = @ArraySchema(schema = @Schema(implementation = OrderResponse.class))
                    )
            )
    })
    @GetMapping
    public ResponseEntity<List<OrderResponse>> getAllOrders() {
        List<OrderResponse> orders = orderService.getAllOrders();
        return ResponseEntity.ok(orders);
    }

    // ============================================================
    // GET /api/orders/{id} — Get one order (with user data)
    // ============================================================

    @Operation(
            summary = "Get order by ID",
            description = "Retrieves a single order with enriched user data from the Provider (User Service). Returns 404 if the order doesn't exist."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "Order found successfully",
                    content = @Content(
                            mediaType = "application/json",
                            schema = @Schema(implementation = OrderResponse.class)
                    )
            ),
            @ApiResponse(
                    responseCode = "404",
                    description = "Order not found",
                    content = @Content(
                            mediaType = "application/json",
                            schema = @Schema(implementation = ErrorResponse.class)
                    )
            )
    })
    @GetMapping("/{id}")
    public ResponseEntity<?> getOrderById(
            @Parameter(description = "Unique order identifier", example = "1")
            @PathVariable Long id) {

        return orderService.getOrderById(id)
                .map(order -> ResponseEntity.ok((Object) order))
                .orElseGet(() -> ResponseEntity
                        .status(HttpStatus.NOT_FOUND)
                        .body(new ErrorResponse(404, "Order not found with id: " + id)));
    }

    // ============================================================
    // POST /api/orders — Create a new order
    // ============================================================

    @Operation(
            summary = "Create a new order",
            description = "Creates a new order. Requires a valid userId that exists in the Provider (User Service). The response includes user data fetched from the Provider."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "201",
                    description = "Order created successfully",
                    content = @Content(
                            mediaType = "application/json",
                            schema = @Schema(implementation = OrderResponse.class)
                    )
            ),
            @ApiResponse(
                    responseCode = "400",
                    description = "Invalid input data (validation failed)",
                    content = @Content(
                            mediaType = "application/json",
                            schema = @Schema(implementation = ErrorResponse.class)
                    )
            )
    })
    @PostMapping
    public ResponseEntity<OrderResponse> createOrder(@Valid @RequestBody Order order) {
        OrderResponse createdOrder = orderService.createOrder(order);
        return ResponseEntity.status(HttpStatus.CREATED).body(createdOrder);
    }

    // ============================================================
    // DELETE /api/orders/{id} — Delete an order
    // ============================================================

    @Operation(
            summary = "Delete an order",
            description = "Permanently deletes an order. Returns 204 on success, 404 if not found."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "204",
                    description = "Order deleted successfully"
            ),
            @ApiResponse(
                    responseCode = "404",
                    description = "Order not found",
                    content = @Content(
                            mediaType = "application/json",
                            schema = @Schema(implementation = ErrorResponse.class)
                    )
            )
    })
    @DeleteMapping("/{id}")
    public ResponseEntity<?> deleteOrder(
            @Parameter(description = "Unique order identifier", example = "1")
            @PathVariable Long id) {

        if (orderService.deleteOrder(id)) {
            return ResponseEntity.noContent().build();
        } else {
            return ResponseEntity
                    .status(HttpStatus.NOT_FOUND)
                    .body(new ErrorResponse(404, "Order not found with id: " + id));
        }
    }
}
