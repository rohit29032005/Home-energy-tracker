INSERT IGNORE INTO `user` (`id`, `name`, `surname`, `email`, `address`, `alerting`, `energy_alerting_threshold`)
VALUES (1, 'Demo', 'Household', 'demo@hometracker.local', 'Smart Energy Demo Home', 1, 25.0);

INSERT IGNORE INTO `device` (`id`, `name`, `type`, `location`, `user_id`)
VALUES
    (1, 'Refrigerator', 'KITCHEN', 'Kitchen', 1),
    (2, 'Air Conditioner', 'HVAC', 'Bedroom', 1),
    (3, 'Smart TV', 'ENTERTAINMENT', 'Living Room', 1),
    (4, 'Desktop Workstation', 'OFFICE', 'Study', 1),
    (5, 'Water Heater', 'UTILITY', 'Bathroom', 1);
