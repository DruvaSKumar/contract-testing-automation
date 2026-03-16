/*
 * ============================================================
 * UserController.java — REST API Controller
 * ============================================================
 * This is the HTTP LAYER of our application. It:
 *   1. Receives incoming HTTP requests (GET, POST, PUT, DELETE)
 *   2. Delegates to UserService for business logic
 *   3. Returns HTTP responses with appropriate status codes
 *
 * WHAT IS @RestController?
 * It combines two annotations:
 *   - @Controller: Marks this as a Spring MVC controller
 *   - @ResponseBody: Return values are written directly to the
 *     HTTP response body as JSON (not rendered as HTML views)
 *
 * WHAT IS @RequestMapping?
 * Sets the BASE PATH for all endpoints in this controller.
 * @RequestMapping("/api/users") means all endpoints start with /api/users
 *
 * OPENAPI ANNOTATIONS (io.swagger.v3.oas.annotations):
 * These annotations enrich the auto-generated OpenAPI specification.
 * They add descriptions, examples, and response schemas that make
 * the spec more useful for our AI Agent when generating contracts.
 * The annotations DON'T change runtime behavior — they only affect
 * the generated documentation.
 * ============================================================
 */
package com.contracttest.provider.controller;

import com.contracttest.provider.model.ErrorResponse;
import com.contracttest.provider.model.User;
import com.contracttest.provider.service.UserService;
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

/**
 * REST controller for User Management operations.
 *
 * ENDPOINTS:
 *   GET    /api/users          → List all users
 *   GET    /api/users/{id}     → Get a specific user
 *   POST   /api/users          → Create a new user
 *   PUT    /api/users/{id}     → Update an existing user
 *   DELETE /api/users/{id}     → Delete a user
 *
 * @Tag adds a category label in the OpenAPI spec / Swagger UI.
 */
@RestController
@RequestMapping("/api/users")
@Tag(name = "User Management", description = "CRUD operations for managing users")
public class UserController {

    /**
     * Dependency Injection — Spring automatically provides a UserService instance.
     *
     * WHY "final" AND CONSTRUCTOR INJECTION?
     * - "final" means this field can't be changed after construction (immutable)
     * - Constructor injection is the recommended way in Spring because:
     *   1. Dependencies are clearly visible
     *   2. The object can't be created without its dependencies
     *   3. Makes testing easier (you can pass mock services)
     */
    private final UserService userService;

    /**
     * Constructor — Spring sees this needs a UserService and automatically
     * injects the @Service bean we defined in UserService.java.
     * No @Autowired needed when there's only one constructor.
     */
    public UserController(UserService userService) {
        this.userService = userService;
    }

    // ============================================================
    // GET /api/users — List all users
    // ============================================================

    /**
     * @Operation describes this endpoint in the OpenAPI spec.
     * @ApiResponses lists all possible HTTP responses with their schemas.
     * These appear in Swagger UI and in the generated spec JSON/YAML.
     */
    @Operation(
            summary = "Get all users",
            description = "Retrieves a list of all users in the system. Returns an empty array if no users exist."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "Successfully retrieved list of users",
                    content = @Content(
                            mediaType = "application/json",
                            array = @ArraySchema(schema = @Schema(implementation = User.class))
                    )
            )
    })
    @GetMapping
    public ResponseEntity<List<User>> getAllUsers() {
        List<User> users = userService.getAllUsers();
        // ResponseEntity lets us control the HTTP status code.
        // .ok() sets status 200 and wraps the body.
        return ResponseEntity.ok(users);
    }

    // ============================================================
    // GET /api/users/{id} — Get a specific user
    // ============================================================

    @Operation(
            summary = "Get user by ID",
            description = "Retrieves a single user by their unique identifier. Returns 404 if not found."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "User found successfully",
                    content = @Content(
                            mediaType = "application/json",
                            schema = @Schema(implementation = User.class)
                    )
            ),
            @ApiResponse(
                    responseCode = "404",
                    description = "User not found",
                    content = @Content(
                            mediaType = "application/json",
                            schema = @Schema(implementation = ErrorResponse.class)
                    )
            )
    })
    @GetMapping("/{id}")
    public ResponseEntity<?> getUserById(
            @Parameter(description = "Unique user identifier", example = "1")
            @PathVariable Long id) {

        /*
         * userService.getUserById() returns Optional<User>.
         *
         * .map(user -> ...) runs if user IS found → returns 200 OK
         * .orElseGet(() -> ...) runs if user is NOT found → returns 404
         *
         * This pattern avoids null checks and is considered best practice.
         */
        return userService.getUserById(id)
                .map(user -> ResponseEntity.ok((Object) user))
                .orElseGet(() -> ResponseEntity
                        .status(HttpStatus.NOT_FOUND)
                        .body(new ErrorResponse(404, "User not found with id: " + id)));
    }

    // ============================================================
    // POST /api/users — Create a new user
    // ============================================================

    @Operation(
            summary = "Create a new user",
            description = "Creates a new user with the provided data. The ID is auto-generated by the server."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "201",
                    description = "User created successfully",
                    content = @Content(
                            mediaType = "application/json",
                            schema = @Schema(implementation = User.class)
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
    public ResponseEntity<User> createUser(
            /*
             * @Valid triggers Jakarta Bean Validation on the User object.
             * If any @NotBlank, @Email, @Size validation fails, Spring
             * throws MethodArgumentNotValidException BEFORE this method runs.
             * Our GlobalExceptionHandler catches it and returns a 400 error.
             *
             * @RequestBody tells Spring to parse the HTTP request body
             * (JSON) and convert it into a User object using Jackson.
             */
            @Valid @RequestBody User user) {

        User createdUser = userService.createUser(user);

        // HttpStatus.CREATED = 201 status code
        // 201 is the standard response for "resource successfully created"
        return ResponseEntity.status(HttpStatus.CREATED).body(createdUser);
    }

    // ============================================================
    // PUT /api/users/{id} — Update an existing user
    // ============================================================

    @Operation(
            summary = "Update an existing user",
            description = "Updates all fields of an existing user. Returns 404 if the user doesn't exist."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "200",
                    description = "User updated successfully",
                    content = @Content(
                            mediaType = "application/json",
                            schema = @Schema(implementation = User.class)
                    )
            ),
            @ApiResponse(
                    responseCode = "400",
                    description = "Invalid input data (validation failed)",
                    content = @Content(
                            mediaType = "application/json",
                            schema = @Schema(implementation = ErrorResponse.class)
                    )
            ),
            @ApiResponse(
                    responseCode = "404",
                    description = "User not found",
                    content = @Content(
                            mediaType = "application/json",
                            schema = @Schema(implementation = ErrorResponse.class)
                    )
            )
    })
    @PutMapping("/{id}")
    public ResponseEntity<?> updateUser(
            @Parameter(description = "Unique user identifier", example = "1")
            @PathVariable Long id,
            @Valid @RequestBody User user) {

        return userService.updateUser(id, user)
                .map(updatedUser -> ResponseEntity.ok((Object) updatedUser))
                .orElseGet(() -> ResponseEntity
                        .status(HttpStatus.NOT_FOUND)
                        .body(new ErrorResponse(404, "User not found with id: " + id)));
    }

    // ============================================================
    // DELETE /api/users/{id} — Delete a user
    // ============================================================

    @Operation(
            summary = "Delete a user",
            description = "Permanently deletes a user. Returns 204 on success, 404 if not found."
    )
    @ApiResponses({
            @ApiResponse(
                    responseCode = "204",
                    description = "User deleted successfully (no response body)"
            ),
            @ApiResponse(
                    responseCode = "404",
                    description = "User not found",
                    content = @Content(
                            mediaType = "application/json",
                            schema = @Schema(implementation = ErrorResponse.class)
                    )
            )
    })
    @DeleteMapping("/{id}")
    public ResponseEntity<?> deleteUser(
            @Parameter(description = "Unique user identifier", example = "1")
            @PathVariable Long id) {

        if (userService.deleteUser(id)) {
            // 204 No Content — standard response for successful deletion
            // No body is returned (the resource no longer exists)
            return ResponseEntity.noContent().build();
        } else {
            return ResponseEntity
                    .status(HttpStatus.NOT_FOUND)
                    .body(new ErrorResponse(404, "User not found with id: " + id));
        }
    }
}
