package com.example;

@RestController
public class HealthController {

    @GetMapping("/health")
    public String health() {
        return "ok";
    }
}
