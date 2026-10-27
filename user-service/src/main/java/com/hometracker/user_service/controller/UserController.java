package com.hometracker.user_service.controller;

import com.hometracker.user_service.dto.UserDto;
import com.hometracker.user_service.security.OwnershipVerifier;
import com.hometracker.user_service.service.UserService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/user")
public class UserController {
    private final UserService userService;
    private final OwnershipVerifier ownershipVerifier;

    public UserController(UserService userService, OwnershipVerifier ownershipVerifier) {
        this.userService = userService;
        this.ownershipVerifier = ownershipVerifier;
    }

    @PostMapping
    public ResponseEntity<UserDto> createUser(@Valid @RequestBody UserDto userDto, HttpServletRequest request) {
        ownershipVerifier.verifyGatewayCanCreate(request);
        UserDto created = userService.createUser(userDto);
        return new ResponseEntity<>(created, HttpStatus.CREATED);
    }

    @GetMapping
    public ResponseEntity<List<UserDto>> getAllUsers(HttpServletRequest request) {
        ownershipVerifier.authenticate(request, false);
        return ResponseEntity.ok(userService.getAllUsers());
    }

    @GetMapping("/{id}")
    public ResponseEntity<UserDto> getUserById(@PathVariable Long id, HttpServletRequest request) {
        OwnershipVerifier.CallerType caller = ownershipVerifier.authenticate(request, true);
        ownershipVerifier.verifyOwnershipForGateway(request, id, caller);
        UserDto userDto = userService.getUserById(id);
        if (userDto == null) {
            return new ResponseEntity<>(HttpStatus.NOT_FOUND);
        }
        return ResponseEntity.ok(userDto);
    }

    @PutMapping("/{id}")
    public ResponseEntity<String> updateUser(@PathVariable Long id,
                                             @Valid @RequestBody UserDto userDto,
                                             HttpServletRequest request) {
        OwnershipVerifier.CallerType caller = ownershipVerifier.authenticate(request, false);
        ownershipVerifier.verifyOwnershipForGateway(request, id, caller);
        try {
            userService.updateUser(id, userDto);
            return ResponseEntity.ok("User updated successfully");
        } catch (IllegalArgumentException e) {
            return new ResponseEntity<>("User not found", HttpStatus.NOT_FOUND);
        }
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteUser(@PathVariable Long id, HttpServletRequest request) {
        OwnershipVerifier.CallerType caller = ownershipVerifier.authenticate(request, false);
        ownershipVerifier.verifyOwnershipForGateway(request, id, caller);
        try {
            userService.deleteUser(id);
            return ResponseEntity.noContent().build();
        } catch (IllegalArgumentException e) {
            return new ResponseEntity<>(HttpStatus.NOT_FOUND);
        }
    }
}
