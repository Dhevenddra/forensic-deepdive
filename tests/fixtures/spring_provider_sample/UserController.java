package com.example;

import java.util.List;

@RestController
@RequestMapping("/api/users")
public class UserController {

    @GetMapping("/{id}")
    public User getUser(Long id) {
        return null;
    }

    @PostMapping
    public User create(User u) {
        return null;
    }

    @RequestMapping(value = "/search", method = RequestMethod.GET)
    public List<User> search() {
        return null;
    }
}
