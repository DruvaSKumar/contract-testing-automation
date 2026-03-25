/*
 * ============================================================
 * UserDTO.java — Data Transfer Object for User (from Provider)
 * ============================================================
 * This class represents the User data that our Order Service
 * RECEIVES from the Provider (User Service) API.
 *
 * WHAT IS A DTO?
 * DTO = Data Transfer Object. It's a class that carries data
 * between services. This UserDTO mirrors the Provider's User
 * model — it has the same fields (id, name, email, role).
 *
 * WHY NOT REUSE THE PROVIDER'S User.java?
 * In a real microservice architecture, each service has its
 * OWN codebase. The Consumer doesn't import Provider code.
 * Instead, it defines its own class that matches the expected
 * response format. This is a fundamental microservice principle:
 * services are INDEPENDENT and don't share code.
 *
 * THIS IS EXACTLY WHAT CONTRACTS PROTECT:
 * If the Provider changes its User model (e.g., renames "name"
 * to "fullName"), this DTO's "name" field would stop receiving
 * data, and things would break silently. Contract tests catch
 * this BEFORE deployment.
 * ============================================================
 */
package com.contracttest.consumer.model;

/**
 * Represents User data received from the Provider (User Service).
 * Fields must match what the Provider's API actually returns.
 */
public class UserDTO {

    /** User's unique ID (as returned by Provider) */
    private Long id;

    /** User's name (as returned by Provider) */
    private String name;

    /** User's email (as returned by Provider) */
    private String email;

    /** User's role (as returned by Provider) */
    private String role;

    // --- Constructors ---

    /** No-arg constructor for Jackson deserialization.
     *  When the Provider's JSON response arrives, Jackson uses
     *  this to create a UserDTO and fill in the fields. */
    public UserDTO() {
    }

    public UserDTO(Long id, String name, String email, String role) {
        this.id = id;
        this.name = name;
        this.email = email;
        this.role = role;
    }

    // --- Getters and Setters ---

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getEmail() {
        return email;
    }

    public void setEmail(String email) {
        this.email = email;
    }

    public String getRole() {
        return role;
    }

    public void setRole(String role) {
        this.role = role;
    }

    @Override
    public String toString() {
        return "UserDTO{id=" + id + ", name='" + name + "', email='" + email + "', role='" + role + "'}";
    }
}
