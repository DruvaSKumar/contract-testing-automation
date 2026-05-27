# ============================================================
# conftest.py — Shared Pytest Fixtures for AI Agent Tests
# ============================================================

import os
import json
import tempfile
import pytest
import yaml


# ---- Sample OpenAPI Spec (minimal but realistic) ----
SAMPLE_OPENAPI_SPEC = {
    "openapi": "3.0.1",
    "info": {
        "title": "User Service API",
        "version": "1.0.0",
    },
    "paths": {
        "/api/users": {
            "get": {
                "tags": ["user-controller"],
                "summary": "Get all users",
                "operationId": "getAllUsers",
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/User"},
                                }
                            }
                        },
                    }
                },
            },
            "post": {
                "tags": ["user-controller"],
                "summary": "Create a new user",
                "operationId": "createUser",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/User"}
                        }
                    },
                    "required": True,
                },
                "responses": {
                    "201": {
                        "description": "Created",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/User"}
                            }
                        },
                    }
                },
            },
        },
        "/api/users/{id}": {
            "get": {
                "tags": ["user-controller"],
                "summary": "Get user by ID",
                "operationId": "getUserById",
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer", "format": "int64"},
                    }
                ],
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/User"}
                            }
                        },
                    },
                    "404": {
                        "description": "Not Found",
                    },
                },
            },
            "put": {
                "tags": ["user-controller"],
                "summary": "Update user",
                "operationId": "updateUser",
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer", "format": "int64"},
                    }
                ],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/User"}
                        }
                    },
                    "required": True,
                },
                "responses": {
                    "200": {
                        "description": "OK",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/User"}
                            }
                        },
                    }
                },
            },
            "delete": {
                "tags": ["user-controller"],
                "summary": "Delete user",
                "operationId": "deleteUser",
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "integer", "format": "int64"},
                    }
                ],
                "responses": {
                    "204": {
                        "description": "No Content",
                    }
                },
            },
        },
    },
    "components": {
        "schemas": {
            "User": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "format": "int64"},
                    "name": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                    "role": {"type": "string", "enum": ["USER", "ADMIN"]},
                },
                "required": ["name", "email"],
            }
        }
    },
}


@pytest.fixture
def sample_spec():
    """Returns the sample OpenAPI spec dict."""
    return SAMPLE_OPENAPI_SPEC.copy()


@pytest.fixture
def spec_file(tmp_path, sample_spec):
    """Creates a temporary JSON file with the sample spec."""
    spec_path = tmp_path / "openapi-spec.json"
    spec_path.write_text(json.dumps(sample_spec), encoding="utf-8")
    return str(spec_path)


@pytest.fixture
def contracts_dir(tmp_path):
    """Creates a temporary contracts directory."""
    contracts = tmp_path / "contracts" / "user"
    contracts.mkdir(parents=True)
    return str(contracts.parent)


@pytest.fixture
def sample_endpoints():
    """Returns a list of parsed endpoints (as the spec_reader would produce)."""
    return [
        {
            "method": "get",
            "path": "/api/users",
            "summary": "Get all users",
            "description": "",
            "operation_id": "getAllUsers",
            "path_parameters": [],
            "request_body_schema": None,
            "responses": {
                "200": {
                    "description": "OK",
                    "schema": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "integer", "format": "int64"},
                                "name": {"type": "string"},
                                "email": {"type": "string", "format": "email"},
                                "role": {"type": "string", "enum": ["USER", "ADMIN"]},
                            },
                            "required": ["name", "email"],
                        },
                    },
                }
            },
            "tags": ["user-controller"],
        },
        {
            "method": "post",
            "path": "/api/users",
            "summary": "Create a new user",
            "description": "",
            "operation_id": "createUser",
            "path_parameters": [],
            "request_body_schema": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "format": "int64"},
                    "name": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                    "role": {"type": "string", "enum": ["USER", "ADMIN"]},
                },
                "required": ["name", "email"],
            },
            "responses": {
                "201": {
                    "description": "Created",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer", "format": "int64"},
                            "name": {"type": "string"},
                            "email": {"type": "string", "format": "email"},
                            "role": {"type": "string", "enum": ["USER", "ADMIN"]},
                        },
                        "required": ["name", "email"],
                    },
                }
            },
            "tags": ["user-controller"],
        },
        {
            "method": "get",
            "path": "/api/users/{id}",
            "summary": "Get user by ID",
            "description": "",
            "operation_id": "getUserById",
            "path_parameters": [
                {"name": "id", "type": "integer", "format": "int64", "required": True}
            ],
            "request_body_schema": None,
            "responses": {
                "200": {
                    "description": "OK",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer", "format": "int64"},
                            "name": {"type": "string"},
                            "email": {"type": "string", "format": "email"},
                            "role": {"type": "string", "enum": ["USER", "ADMIN"]},
                        },
                        "required": ["name", "email"],
                    },
                },
                "404": {"description": "Not Found", "schema": None},
            },
            "tags": ["user-controller"],
        },
        {
            "method": "put",
            "path": "/api/users/{id}",
            "summary": "Update user",
            "description": "",
            "operation_id": "updateUser",
            "path_parameters": [
                {"name": "id", "type": "integer", "format": "int64", "required": True}
            ],
            "request_body_schema": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "format": "int64"},
                    "name": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                    "role": {"type": "string", "enum": ["USER", "ADMIN"]},
                },
                "required": ["name", "email"],
            },
            "responses": {
                "200": {
                    "description": "OK",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer", "format": "int64"},
                            "name": {"type": "string"},
                            "email": {"type": "string", "format": "email"},
                            "role": {"type": "string", "enum": ["USER", "ADMIN"]},
                        },
                        "required": ["name", "email"],
                    },
                }
            },
            "tags": ["user-controller"],
        },
        {
            "method": "delete",
            "path": "/api/users/{id}",
            "summary": "Delete user",
            "description": "",
            "operation_id": "deleteUser",
            "path_parameters": [
                {"name": "id", "type": "integer", "format": "int64", "required": True}
            ],
            "request_body_schema": None,
            "responses": {
                "204": {"description": "No Content", "schema": None}
            },
            "tags": ["user-controller"],
        },
    ]


@pytest.fixture
def sample_contract_yaml():
    """Returns a sample contract YAML content as a dict."""
    return {
        "description": "Should return all users",
        "name": "should_return_all_users",
        "request": {
            "method": "GET",
            "url": "/api/users",
            "headers": {"Content-Type": "application/json"},
        },
        "response": {
            "status": 200,
            "headers": {"Content-Type": "application/json"},
            "body": [
                {"id": 1, "name": "Sample User", "email": "sample@example.com", "role": "USER"}
            ],
        },
    }


@pytest.fixture
def populated_contracts_dir(contracts_dir, sample_contract_yaml):
    """Creates a contracts directory with sample contract files."""
    user_dir = os.path.join(contracts_dir, "user")
    os.makedirs(user_dir, exist_ok=True)

    contracts = [
        {
            "filename": "should_return_all_users.yml",
            "content": {
                "description": "Should return all users",
                "name": "should_return_all_users",
                "request": {"method": "GET", "url": "/api/users"},
                "response": {"status": 200, "headers": {"Content-Type": "application/json"},
                             "body": [{"id": 1, "name": "Alice", "email": "alice@test.com"}]},
            },
        },
        {
            "filename": "should_create_a_new_user.yml",
            "content": {
                "description": "Should create a new user",
                "name": "should_create_a_new_user",
                "request": {"method": "POST", "url": "/api/users"},
                "response": {"status": 201, "headers": {"Content-Type": "application/json"},
                             "body": {"id": 1, "name": "Alice", "email": "alice@test.com"}},
            },
        },
        {
            "filename": "should_return_user_by_id.yml",
            "content": {
                "description": "Should return user by ID",
                "name": "should_return_user_by_id",
                "request": {"method": "GET", "url": "/api/users/1"},
                "response": {"status": 200, "headers": {"Content-Type": "application/json"},
                             "body": {"id": 1, "name": "Alice", "email": "alice@test.com"}},
            },
        },
        {
            "filename": "should_update_user.yml",
            "content": {
                "description": "Should update user",
                "name": "should_update_user",
                "request": {"method": "PUT", "url": "/api/users/1"},
                "response": {"status": 200, "headers": {"Content-Type": "application/json"},
                             "body": {"id": 1, "name": "Updated", "email": "updated@test.com"}},
            },
        },
        {
            "filename": "should_delete_user.yml",
            "content": {
                "description": "Should delete user",
                "name": "should_delete_user",
                "request": {"method": "DELETE", "url": "/api/users/1"},
                "response": {"status": 204},
            },
        },
    ]

    for contract in contracts:
        filepath = os.path.join(user_dir, contract["filename"])
        with open(filepath, "w", encoding="utf-8") as f:
            yaml.dump(contract["content"], f, default_flow_style=False)

    return contracts_dir
