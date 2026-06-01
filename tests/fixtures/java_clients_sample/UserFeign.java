package com.example.client;

import org.springframework.cloud.openfeign.FeignClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import feign.RequestLine;

@FeignClient(name = "users")
@RequestMapping("/api")
interface UserFeign {

  @GetMapping("/users/{id}")
  User get(String id);

  @RequestLine("POST /users")
  void create(User u);
}
