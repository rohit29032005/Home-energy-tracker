-- Local Keycloak realm fixture `demo-user-two` maps to this separate profile.
-- INSERT IGNORE keeps existing deployments unchanged.
INSERT IGNORE INTO `user` (`id`, `name`, `surname`, `email`, `address`, `alerting`, `energy_alerting_threshold`)
VALUES (2, 'Demo', 'Household Two', 'demo-user-two@hometracker.local', 'Second Smart Energy Demo Home', 1, 25.0);
