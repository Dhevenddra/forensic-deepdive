package com.example;

import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/admin")
public class AdminController {

  // Bare @RequestMapping (no method=) → handles all verbs → http::*::/admin/stats
  @RequestMapping("/stats")
  public Stats getStats() {
    return null;
  }
}
