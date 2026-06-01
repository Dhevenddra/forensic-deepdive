package com.example;

import org.springframework.web.client.RestTemplate;

public class OrderClient {
  private RestTemplate restTemplate;

  public Order fetchOrder(String id) {
    return restTemplate.getForObject("/spring/orders/{id}", Order.class, id);
  }

  public Order sendOrder(Order o) {
    return restTemplate.postForObject("/spring/orders", o, Order.class);
  }
}
