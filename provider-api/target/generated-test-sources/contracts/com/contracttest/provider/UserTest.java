package com.contracttest.provider;

import com.contracttest.provider.BaseContractTest;
import com.jayway.jsonpath.DocumentContext;
import com.jayway.jsonpath.JsonPath;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import io.restassured.module.mockmvc.specification.MockMvcRequestSpecification;
import io.restassured.response.ResponseOptions;

import static org.springframework.cloud.contract.verifier.assertion.SpringCloudContractAssertions.assertThat;
import static org.springframework.cloud.contract.verifier.util.ContractVerifierUtil.*;
import static com.toomuchcoding.jsonassert.JsonAssertion.assertThatJson;
import static io.restassured.module.mockmvc.RestAssuredMockMvc.*;

@SuppressWarnings("rawtypes")
public class UserTest extends BaseContractTest {

	@Test
	public void validate_should_create_a_new_user() throws Exception {
		// given:
			MockMvcRequestSpecification request = given()
					.header("Content-Type", "application/json")
					.body("{\"name\":\"Dave Wilson\",\"email\":\"dave@example.com\",\"role\":\"USER\"}");

		// when:
			ResponseOptions response = given().spec(request)

					.post("/api/users");

		// then:
			assertThat(response.statusCode()).isEqualTo(201);
			assertThat(response.header("Content-Type")).isEqualTo("application/json");


		// and:
			DocumentContext parsedJson = JsonPath.parse(response.getBody().asString());
			assertThatJson(parsedJson).field("['name']").isEqualTo("Dave Wilson");
			assertThatJson(parsedJson).field("['email']").isEqualTo("dave@example.com");
			assertThatJson(parsedJson).field("['role']").isEqualTo("USER");

		// and:
			assertThat(parsedJson.read("$.id", String.class)).matches("[0-9]+");
	}

	@Test
	public void validate_should_return_all_users() throws Exception {
		// given:
			MockMvcRequestSpecification request = given();


		// when:
			ResponseOptions response = given().spec(request)

					.get("/api/users");

		// then:
			assertThat(response.statusCode()).isEqualTo(200);
			assertThat(response.header("Content-Type")).isEqualTo("application/json");


		// and:
			DocumentContext parsedJson = JsonPath.parse(response.getBody().asString());
			assertThatJson(parsedJson).array().contains("['id']").isEqualTo(1);
			assertThatJson(parsedJson).array().contains("['name']").isEqualTo("Alice Johnson");
			assertThatJson(parsedJson).array().contains("['email']").isEqualTo("alice@example.com");
			assertThatJson(parsedJson).array().contains("['role']").isEqualTo("ADMIN");
			assertThatJson(parsedJson).array().contains("['id']").isEqualTo(2);
			assertThatJson(parsedJson).array().contains("['name']").isEqualTo("Bob Smith");
			assertThatJson(parsedJson).array().contains("['email']").isEqualTo("bob@example.com");
			assertThatJson(parsedJson).array().contains("['role']").isEqualTo("USER");
			assertThatJson(parsedJson).array().contains("['id']").isEqualTo(3);
			assertThatJson(parsedJson).array().contains("['name']").isEqualTo("Charlie Brown");
			assertThatJson(parsedJson).array().contains("['email']").isEqualTo("charlie@example.com");
			assertThatJson(parsedJson).array().contains("['role']").isEqualTo("MANAGER");
	}

	@Test
	public void validate_should_return_user_by_id() throws Exception {
		// given:
			MockMvcRequestSpecification request = given();


		// when:
			ResponseOptions response = given().spec(request)

					.get("/api/users/1");

		// then:
			assertThat(response.statusCode()).isEqualTo(200);
			assertThat(response.header("Content-Type")).isEqualTo("application/json");


		// and:
			DocumentContext parsedJson = JsonPath.parse(response.getBody().asString());

		// and:
			assertThat(parsedJson.read("$.id", String.class)).matches("[0-9]+");
			assertThat(parsedJson.read("$.name", String.class)).matches(".+");
			assertThat(parsedJson.read("$.email", String.class)).matches("[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}");
			assertThat(parsedJson.read("$.role", String.class)).matches(".+");
	}

}
