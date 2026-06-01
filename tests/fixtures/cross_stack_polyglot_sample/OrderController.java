package com.example;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/spring/orders")
public class OrderController {

  @GetMapping("/{id}")
  public Order getOrder(String id) {
    return null;
  }

  @PostMapping
  public Order createOrder(Order o) {
    return o;
  }
}
