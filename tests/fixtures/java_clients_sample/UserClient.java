package com.example.client;

import org.springframework.web.client.RestTemplate;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.http.HttpMethod;

public class UserClient {
  private RestTemplate restTemplate;
  private WebClient webClient;

  public User getUser(String id) {
    return restTemplate.getForObject("/api/users/{id}", User.class, id);
  }

  public User addUser(User u) {
    return restTemplate.postForObject("/api/users", u, User.class);
  }

  public void removeUser() {
    restTemplate.exchange("/api/users/1", HttpMethod.DELETE, null, Void.class);
  }

  public Mono<User> fetchThings() {
    return webClient.get().uri("/api/things").retrieve().bodyToMono(User.class);
  }

  public User dynamic(String id) {
    return restTemplate.getForObject("/api/users/" + id, User.class);
  }

  public String health() {
    return restTemplate.getForObject("/health", String.class);
  }
}
