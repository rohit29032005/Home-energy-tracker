package com.hometracker.alert_service.repository;

import com.hometracker.alert_service.entity.Alert;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.Optional;

public interface AlertRepository extends JpaRepository<Alert, Long> {
    List<Alert> findByUserIdOrderByCreatedAtDesc(Long userId);
    Optional<Alert> findTopByDeduplicationKeyOrderByCreatedAtDesc(String deduplicationKey);
}

