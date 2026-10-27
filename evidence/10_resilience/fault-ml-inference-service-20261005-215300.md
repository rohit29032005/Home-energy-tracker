# Controlled fault injection: ml-inference-service

Started: 2026-10-05T21:53:00.5992271+05:30
NAME                   IMAGE                                                                     COMMAND                  SERVICE                CREATED          STATUS                    PORTS
alert-service          home-energy-tracker-alert-service                                         "java -jar app.jar"      alert-service          46 minutes ago   Up 46 minutes             8085/tcp
api-gateway            home-energy-tracker-api-gateway                                           "java -jar app.jar"      api-gateway            16 minutes ago   Up 16 minutes             0.0.0.0:8080->8080/tcp, [::]:8080->8080/tcp
device-service         home-energy-tracker-device-service                                        "java -jar app.jar"      device-service         47 minutes ago   Up 47 minutes             8082/tcp
grafana                grafana/grafana:11.2.0                                                    "/run.sh"                grafana                42 hours ago     Up 33 minutes             0.0.0.0:3001->3000/tcp, [::]:3001->3000/tcp
home-energy-frontend   sha256:1be7293f215b9b0a054b1920cd4aa5cec550ab503be05bf44bf68f27cfe75228   "/docker-entrypoint.…"   frontend               10 days ago      Up 33 minutes             0.0.0.0:3000->80/tcp, [::]:3000->80/tcp
influxdb               influxdb:2.7                                                              "/entrypoint.sh infl…"   influxdb               52 minutes ago   Up 51 minutes (healthy)   0.0.0.0:8072->8086/tcp, [::]:8072->8086/tcp
ingestion-service      home-energy-tracker-ingestion-service                                     "java -jar app.jar"      ingestion-service      20 hours ago     Up 20 hours               8083/tcp
insight-service        home-energy-tracker-insight-service                                       "java -jar app.jar"      insight-service        19 hours ago     Up 19 hours               8086/tcp
kafka                  apache/kafka:latest                                                       "/__cacert_entrypoin…"   kafka                  20 hours ago     Up 20 hours               0.0.0.0:9092->9092/tcp, [::]:9092->9092/tcp, 0.0.0.0:9094->9094/tcp, [::]:9094->9094/tcp
kafka-ui               ghcr.io/kafbat/kafka-ui:latest                                            "/bin/sh -c 'java --…"   kafka-ui               19 hours ago     Up 19 hours               0.0.0.0:8070->8080/tcp, [::]:8070->8080/tcp
keycloak               quay.io/keycloak/keycloak:26.0.7                                          "/opt/keycloak/bin/k…"   keycloak               42 hours ago     Up 20 hours               0.0.0.0:8180->8080/tcp, [::]:8180->8080/tcp
mailpit                axllent/mailpit:latest                                                    "/mailpit"               mailpit                43 minutes ago   Up 38 seconds (healthy)   0.0.0.0:1025->1025/tcp, [::]:1025->1025/tcp, 0.0.0.0:8025->8025/tcp, [::]:8025->8025/tcp
ml-inference-service   home-energy-tracker-ml-inference-service                                  "uvicorn app.main:ap…"   ml-inference-service   46 minutes ago   Up 46 minutes             8090/tcp
mysql                  mysql:8.3.0                                                               "docker-entrypoint.s…"   mysql                  10 days ago      Up 20 hours (healthy)     0.0.0.0:3306->3306/tcp, [::]:3306->3306/tcp
prometheus             prom/prometheus:v2.54.1                                                   "/bin/prometheus --c…"   prometheus             42 hours ago     Up 33 minutes             0.0.0.0:9090->9090/tcp, [::]:9090->9090/tcp
usage-service          home-energy-tracker-usage-service                                         "java -jar app.jar"      usage-service          50 minutes ago   Up 50 minutes             8084/tcp
user-service           home-energy-tracker-user-service                                          "java -jar app.jar"      user-service           20 hours ago     Up 20 hours               8081/tcp


## State while ml-inference-service was stopped
Ingestion HTTP status while faulted: 201
api-gateway        | 
api-gateway        |   .   ____          _            __ _ _
api-gateway        |  /\\ / ___'_ __ _ _(_)_ __  __ _ \ \ \ \
api-gateway        | ( ( )\___ | '_ | '_| | '_ \/ _` | \ \ \ \
api-gateway        |  \\/  ___)| |_)| | | | | || (_| |  ) ) ) )
api-gateway        |   '  |____| .__|_| |_|_| |_\__, | / / / /
api-gateway        |  =========|_|==============|___/=/_/_/_/
api-gateway        | 
api-gateway        |  :: Spring Boot ::                (v3.4.5)
api-gateway        | 
api-gateway        | 2026-10-05 16:06:52.674 [] INFO  c.h.a.ApiGatewayApplication - Starting ApiGatewayApplication v0.0.1-SNAPSHOT using Java 17.0.20.1 with PID 1 (/app/app.jar started by root in /app)
api-gateway        | 2026-10-05 16:06:52.682 [] INFO  c.h.a.ApiGatewayApplication - No active profile set, falling back to 1 default profile: "default"
api-gateway        | 2026-10-05 16:06:57.132 [] INFO  o.s.cloud.context.scope.GenericScope - BeanFactory id=ed23e62b-4820-33b0-a1f5-ac6106586640
api-gateway        | 2026-10-05 16:06:59.612 [] INFO  o.s.b.f.a.AutowiredAnnotationBeanPostProcessor - Inconsistent constructor declaration on bean with name '_reactiveMethodSecurityConfiguration': single autowire-marked constructor flagged as optional - this constructor is effectively required since there is no default constructor to fall back to: org.springframework.security.config.annotation.method.configuration.ReactiveAuthorizationManagerMethodSecurityConfiguration(org.springframework.security.access.expression.method.MethodSecurityExpressionHandler,org.springframework.beans.factory.ObjectProvider,org.springframework.beans.factory.ObjectProvider)
api-gateway        | 2026-10-05 16:07:00.482 [] INFO  o.s.c.g.r.RouteDefinitionRouteLocator - Loaded RoutePredicateFactory [After]
api-gateway        | 2026-10-05 16:07:00.483 [] INFO  o.s.c.g.r.RouteDefinitionRouteLocator - Loaded RoutePredicateFactory [Before]
api-gateway        | 2026-10-05 16:07:00.483 [] INFO  o.s.c.g.r.RouteDefinitionRouteLocator - Loaded RoutePredicateFactory [Between]
api-gateway        | 2026-10-05 16:07:00.483 [] INFO  o.s.c.g.r.RouteDefinitionRouteLocator - Loaded RoutePredicateFactory [Cookie]
api-gateway        | 2026-10-05 16:07:00.483 [] INFO  o.s.c.g.r.RouteDefinitionRouteLocator - Loaded RoutePredicateFactory [Header]
api-gateway        | 2026-10-05 16:07:00.483 [] INFO  o.s.c.g.r.RouteDefinitionRouteLocator - Loaded RoutePredicateFactory [Host]
api-gateway        | 2026-10-05 16:07:00.483 [] INFO  o.s.c.g.r.RouteDefinitionRouteLocator - Loaded RoutePredicateFactory [Method]
api-gateway        | 2026-10-05 16:07:00.483 [] INFO  o.s.c.g.r.RouteDefinitionRouteLocator - Loaded RoutePredicateFactory [Path]
api-gateway        | 2026-10-05 16:07:00.484 [] INFO  o.s.c.g.r.RouteDefinitionRouteLocator - Loaded RoutePredicateFactory [Query]
api-gateway        | 2026-10-05 16:07:00.484 [] INFO  o.s.c.g.r.RouteDefinitionRouteLocator - Loaded RoutePredicateFactory [ReadBody]
api-gateway        | 2026-10-05 16:07:00.484 [] INFO  o.s.c.g.r.RouteDefinitionRouteLocator - Loaded RoutePredicateFactory [RemoteAddr]
api-gateway        | 2026-10-05 16:07:00.484 [] INFO  o.s.c.g.r.RouteDefinitionRouteLocator - Loaded RoutePredicateFactory [XForwardedRemoteAddr]
api-gateway        | 2026-10-05 16:07:00.484 [] INFO  o.s.c.g.r.RouteDefinitionRouteLocator - Loaded RoutePredicateFactory [Weight]
api-gateway        | 2026-10-05 16:07:00.484 [] INFO  o.s.c.g.r.RouteDefinitionRouteLocator - Loaded RoutePredicateFactory [CloudFoundryRouteService]
api-gateway        | 2026-10-05 16:07:00.682 [] WARN  o.s.w.r.r.ResourceHandlerUtils - Appended trailing slash to static resource location: classpath:/META-INF/resources/webjars/swagger-ui/5.18.3/
api-gateway        | 2026-10-05 16:07:01.154 [] INFO  o.s.b.a.e.web.EndpointLinksResolver - Exposing 4 endpoints beneath base path '/actuator'
api-gateway        | 2026-10-05 16:07:02.171 [] INFO  o.s.b.w.e.netty.NettyWebServer - Netty started on port 8080 (http)
api-gateway        | 2026-10-05 16:07:02.322 [] INFO  c.h.a.ApiGatewayApplication - Started ApiGatewayApplication in 10.732 seconds (process running for 13.652)
usage-service      | 2026-10-05 16:20:00.410 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 16
usage-service      | 2026-10-05 16:20:00.460 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 13
usage-service      | 2026-10-05 16:20:00.481 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 14
usage-service      | 2026-10-05 16:20:00.510 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 15
usage-service      | 2026-10-05 16:20:00.510 [] INFO  c.h.u.service.UsageService - User Threshold Map: {1=25.0}
usage-service      | 2026-10-05 16:20:00.510 [] INFO  c.h.u.service.UsageService - ALERT: User ID 1 has exceeded the energy threshold! Total Consumption: 114.9170704005161, Threshold: 25.0
usage-service      | 2026-10-05 16:20:10.176 [] INFO  c.h.u.service.UsageService - Aggregated device energies over the past hour: [DeviceEnergy(deviceId=1, energyConsumed=113.9170704005161, userId=null), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=null)]
usage-service      | 2026-10-05 16:20:10.325 [] INFO  c.h.u.service.UsageService - User-Device Energy Map: {16=[DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=16)], 1=[DeviceEnergy(deviceId=1, energyConsumed=113.9170704005161, userId=1), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=1)], 13=[DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=13)], 14=[DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=14)], 15=[DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=15)]}
usage-service      | 2026-10-05 16:20:10.340 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 16
usage-service      | 2026-10-05 16:20:10.365 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 13
usage-service      | 2026-10-05 16:20:10.400 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 14
usage-service      | 2026-10-05 16:20:10.412 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 15
usage-service      | 2026-10-05 16:20:10.413 [] INFO  c.h.u.service.UsageService - User Threshold Map: {1=25.0}
usage-service      | 2026-10-05 16:20:10.413 [] INFO  c.h.u.service.UsageService - ALERT: User ID 1 has exceeded the energy threshold! Total Consumption: 114.9170704005161, Threshold: 25.0
usage-service      | 2026-10-05 16:20:20.214 [] INFO  c.h.u.service.UsageService - Aggregated device energies over the past hour: [DeviceEnergy(deviceId=1, energyConsumed=113.9170704005161, userId=null), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=null)]
usage-service      | 2026-10-05 16:20:20.355 [] INFO  c.h.u.service.UsageService - User-Device Energy Map: {16=[DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=16)], 1=[DeviceEnergy(deviceId=1, energyConsumed=113.9170704005161, userId=1), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=1)], 13=[DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=13)], 14=[DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=14)], 15=[DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=15)]}
usage-service      | 2026-10-05 16:20:20.376 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 16
usage-service      | 2026-10-05 16:20:20.406 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 13
usage-service      | 2026-10-05 16:20:20.415 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 14
usage-service      | 2026-10-05 16:20:20.424 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 15
usage-service      | 2026-10-05 16:20:20.424 [] INFO  c.h.u.service.UsageService - User Threshold Map: {1=25.0}
usage-service      | 2026-10-05 16:20:20.426 [] INFO  c.h.u.service.UsageService - ALERT: User ID 1 has exceeded the energy threshold! Total Consumption: 114.9170704005161, Threshold: 25.0
usage-service      | 2026-10-05 16:20:30.220 [] INFO  c.h.u.service.UsageService - Aggregated device energies over the past hour: [DeviceEnergy(deviceId=1, energyConsumed=113.9170704005161, userId=null), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=null)]
usage-service      | 2026-10-05 16:20:30.347 [] INFO  c.h.u.service.UsageService - User-Device Energy Map: {16=[DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=16)], 1=[DeviceEnergy(deviceId=1, energyConsumed=113.9170704005161, userId=1), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=1)], 13=[DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=13)], 14=[DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=14)], 15=[DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=15)]}
usage-service      | 2026-10-05 16:20:30.364 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 16
usage-service      | 2026-10-05 16:20:30.409 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 13
usage-service      | 2026-10-05 16:20:30.426 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 14
usage-service      | 2026-10-05 16:20:30.448 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 15
usage-service      | 2026-10-05 16:20:30.448 [] INFO  c.h.u.service.UsageService - User Threshold Map: {1=25.0}
usage-service      | 2026-10-05 16:20:30.449 [] INFO  c.h.u.service.UsageService - ALERT: User ID 1 has exceeded the energy threshold! Total Consumption: 114.9170704005161, Threshold: 25.0
usage-service      | 2026-10-05 16:20:42.347 [] INFO  c.h.u.service.UsageService - Aggregated device energies over the past hour: [DeviceEnergy(deviceId=1, energyConsumed=113.9170704005161, userId=null), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=null)]
usage-service      | 2026-10-05 16:20:42.679 [] INFO  c.h.u.service.UsageService - User-Device Energy Map: {16=[DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=16)], 1=[DeviceEnergy(deviceId=1, energyConsumed=113.9170704005161, userId=1), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=1)], 13=[DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=13)], 14=[DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=14)], 15=[DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=15)]}
usage-service      | 2026-10-05 16:20:42.765 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 16
usage-service      | 2026-10-05 16:20:42.813 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 13
usage-service      | 2026-10-05 16:20:42.835 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 14
usage-service      | 2026-10-05 16:20:42.857 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 15
usage-service      | 2026-10-05 16:20:42.857 [] INFO  c.h.u.service.UsageService - User Threshold Map: {1=25.0}
usage-service      | 2026-10-05 16:20:42.859 [] INFO  c.h.u.service.UsageService - ALERT: User ID 1 has exceeded the energy threshold! Total Consumption: 114.9170704005161, Threshold: 25.0
usage-service      | 2026-10-05 16:20:50.553 [] INFO  c.h.u.service.UsageService - Aggregated device energies over the past hour: [DeviceEnergy(deviceId=1, energyConsumed=114.2270704005161, userId=null), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=null)]
usage-service      | 2026-10-05 16:20:50.841 [] INFO  c.h.u.service.UsageService - User-Device Energy Map: {16=[DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=16)], 1=[DeviceEnergy(deviceId=1, energyConsumed=114.2270704005161, userId=1), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=1)], 13=[DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=13)], 14=[DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=14)], 15=[DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=15)]}
usage-service      | 2026-10-05 16:20:50.873 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 16
usage-service      | 2026-10-05 16:20:50.917 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 13
ingestion-service  | 2026-10-05 16:18:57.170 [k6-1-30] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2879527402375848, timestamp=2026-10-05T16:18:57.160Z]
ingestion-service  | 2026-10-05 16:18:57.288 [k6-5-30] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2587479975122984, timestamp=2026-10-05T16:18:57.275Z]
ingestion-service  | 2026-10-05 16:18:57.377 [k6-10-30] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2620702667344697, timestamp=2026-10-05T16:18:57.365Z]
ingestion-service  | 2026-10-05 16:18:57.488 [k6-2-30] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2323616833359614, timestamp=2026-10-05T16:18:57.478Z]
ingestion-service  | 2026-10-05 16:18:57.603 [k6-9-30] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2955546388028184, timestamp=2026-10-05T16:18:57.591Z]
ingestion-service  | 2026-10-05 16:18:57.719 [k6-6-30] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.20427887859285918, timestamp=2026-10-05T16:18:57.705Z]
ingestion-service  | 2026-10-05 16:18:57.829 [k6-4-30] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2223408672144946, timestamp=2026-10-05T16:18:57.818Z]
ingestion-service  | 2026-10-05 16:18:57.943 [k6-7-31] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.23361531223047005, timestamp=2026-10-05T16:18:57.932Z]
ingestion-service  | 2026-10-05 16:18:58.059 [k6-3-31] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.28884725453800764, timestamp=2026-10-05T16:18:58.044Z]
ingestion-service  | 2026-10-05 16:18:58.171 [k6-8-31] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2719587638530129, timestamp=2026-10-05T16:18:58.156Z]
ingestion-service  | 2026-10-05 16:18:58.282 [k6-1-31] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.26644631793805246, timestamp=2026-10-05T16:18:58.268Z]
ingestion-service  | 2026-10-05 16:18:58.401 [k6-5-31] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.22638941873350404, timestamp=2026-10-05T16:18:58.381Z]
ingestion-service  | 2026-10-05 16:18:58.508 [k6-10-31] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.27986345039152943, timestamp=2026-10-05T16:18:58.493Z]
ingestion-service  | 2026-10-05 16:18:58.619 [k6-2-31] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2012342340292603, timestamp=2026-10-05T16:18:58.603Z]
ingestion-service  | 2026-10-05 16:18:58.728 [k6-9-31] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.235181887539562, timestamp=2026-10-05T16:18:58.715Z]
ingestion-service  | 2026-10-05 16:18:58.836 [k6-6-31] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.23239298837224664, timestamp=2026-10-05T16:18:58.826Z]
ingestion-service  | 2026-10-05 16:18:58.967 [k6-4-31] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.24133296990113204, timestamp=2026-10-05T16:18:58.937Z]
ingestion-service  | 2026-10-05 16:18:59.064 [k6-7-32] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.29619090341586835, timestamp=2026-10-05T16:18:59.047Z]
ingestion-service  | 2026-10-05 16:18:59.169 [k6-3-32] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.24507652705286534, timestamp=2026-10-05T16:18:59.157Z]
ingestion-service  | 2026-10-05 16:18:59.280 [k6-8-32] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2961770293780897, timestamp=2026-10-05T16:18:59.268Z]
ingestion-service  | 2026-10-05 16:18:59.389 [k6-1-32] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.28247292108981925, timestamp=2026-10-05T16:18:59.377Z]
ingestion-service  | 2026-10-05 16:18:59.502 [k6-5-32] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2680540687273106, timestamp=2026-10-05T16:18:59.487Z]
ingestion-service  | 2026-10-05 16:18:59.610 [k6-10-32] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.21294627112067022, timestamp=2026-10-05T16:18:59.597Z]
ingestion-service  | 2026-10-05 16:18:59.716 [k6-2-32] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.20499417322567076, timestamp=2026-10-05T16:18:59.706Z]
ingestion-service  | 2026-10-05 16:18:59.826 [k6-9-32] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.20504604908324445, timestamp=2026-10-05T16:18:59.815Z]
ingestion-service  | 2026-10-05 16:18:59.935 [k6-6-32] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.24510770578403024, timestamp=2026-10-05T16:18:59.923Z]
usage-service      | 2026-10-05 16:20:50.944 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 14
usage-service      | 2026-10-05 16:20:50.968 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 15
usage-service      | 2026-10-05 16:20:50.968 [] INFO  c.h.u.service.UsageService - User Threshold Map: {1=25.0}
usage-service      | 2026-10-05 16:20:50.969 [] INFO  c.h.u.service.UsageService - ALERT: User ID 1 has exceeded the energy threshold! Total Consumption: 115.2270704005161, Threshold: 25.0
usage-service      | 2026-10-05 16:21:00.231 [] INFO  c.h.u.service.UsageService - Aggregated device energies over the past hour: [DeviceEnergy(deviceId=1, energyConsumed=114.2270704005161, userId=null), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=null)]
usage-service      | 2026-10-05 16:21:00.363 [] INFO  c.h.u.service.UsageService - User-Device Energy Map: {16=[DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=16)], 1=[DeviceEnergy(deviceId=1, energyConsumed=114.2270704005161, userId=1), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=1)], 13=[DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=13)], 14=[DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=14)], 15=[DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=15)]}
usage-service      | 2026-10-05 16:21:00.378 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 16
usage-service      | 2026-10-05 16:21:00.398 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 13
usage-service      | 2026-10-05 16:21:00.407 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 14
usage-service      | 2026-10-05 16:21:00.415 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 15
usage-service      | 2026-10-05 16:21:00.416 [] INFO  c.h.u.service.UsageService - User Threshold Map: {1=25.0}
usage-service      | 2026-10-05 16:21:00.416 [] INFO  c.h.u.service.UsageService - ALERT: User ID 1 has exceeded the energy threshold! Total Consumption: 115.2270704005161, Threshold: 25.0
usage-service      | 2026-10-05 16:21:10.282 [] INFO  c.h.u.service.UsageService - Aggregated device energies over the past hour: [DeviceEnergy(deviceId=1, energyConsumed=114.2270704005161, userId=null), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=null)]
usage-service      | 2026-10-05 16:21:10.388 [] INFO  c.h.u.service.UsageService - User-Device Energy Map: {16=[DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=16)], 1=[DeviceEnergy(deviceId=1, energyConsumed=114.2270704005161, userId=1), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=1)], 13=[DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=13)], 14=[DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=14)], 15=[DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=15)]}
usage-service      | 2026-10-05 16:21:10.399 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 16
usage-service      | 2026-10-05 16:21:10.424 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 13
usage-service      | 2026-10-05 16:21:10.434 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 14
usage-service      | 2026-10-05 16:21:10.455 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 15
usage-service      | 2026-10-05 16:21:10.455 [] INFO  c.h.u.service.UsageService - User Threshold Map: {1=25.0}
usage-service      | 2026-10-05 16:21:10.455 [] INFO  c.h.u.service.UsageService - ALERT: User ID 1 has exceeded the energy threshold! Total Consumption: 115.2270704005161, Threshold: 25.0
usage-service      | 2026-10-05 16:21:25.073 [] INFO  c.h.u.service.UsageService - Aggregated device energies over the past hour: [DeviceEnergy(deviceId=1, energyConsumed=114.2270704005161, userId=null), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=null)]
usage-service      | 2026-10-05 16:21:25.239 [] INFO  c.h.u.service.UsageService - User-Device Energy Map: {16=[DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=16)], 1=[DeviceEnergy(deviceId=1, energyConsumed=114.2270704005161, userId=1), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=1)], 13=[DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=13)], 14=[DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=14)], 15=[DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=15)]}
usage-service      | 2026-10-05 16:21:25.305 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 16
usage-service      | 2026-10-05 16:21:25.360 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 13
usage-service      | 2026-10-05 16:21:25.389 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 14
usage-service      | 2026-10-05 16:21:25.415 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 15
usage-service      | 2026-10-05 16:21:25.416 [] INFO  c.h.u.service.UsageService - User Threshold Map: {1=25.0}
usage-service      | 2026-10-05 16:21:25.416 [] INFO  c.h.u.service.UsageService - ALERT: User ID 1 has exceeded the energy threshold! Total Consumption: 115.2270704005161, Threshold: 25.0
usage-service      | 2026-10-05 16:21:30.201 [] INFO  c.h.u.service.UsageService - Aggregated device energies over the past hour: [DeviceEnergy(deviceId=1, energyConsumed=114.2270704005161, userId=null), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=null)]
usage-service      | 2026-10-05 16:21:30.363 [] INFO  c.h.u.service.UsageService - User-Device Energy Map: {16=[DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=16)], 1=[DeviceEnergy(deviceId=1, energyConsumed=114.2270704005161, userId=1), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=1)], 13=[DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=13)], 14=[DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=14)], 15=[DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=15)]}
usage-service      | 2026-10-05 16:21:30.378 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 16
usage-service      | 2026-10-05 16:21:30.405 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 13
usage-service      | 2026-10-05 16:21:30.424 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 14
usage-service      | 2026-10-05 16:21:30.436 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 15
usage-service      | 2026-10-05 16:21:30.436 [] INFO  c.h.u.service.UsageService - User Threshold Map: {1=25.0}
usage-service      | 2026-10-05 16:21:30.437 [] INFO  c.h.u.service.UsageService - ALERT: User ID 1 has exceeded the energy threshold! Total Consumption: 115.2270704005161, Threshold: 25.0
usage-service      | 2026-10-05 16:21:40.213 [] INFO  c.h.u.service.UsageService - Aggregated device energies over the past hour: [DeviceEnergy(deviceId=1, energyConsumed=114.2270704005161, userId=null), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=null)]
usage-service      | 2026-10-05 16:21:40.370 [] INFO  c.h.u.service.UsageService - User-Device Energy Map: {16=[DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=16)], 1=[DeviceEnergy(deviceId=1, energyConsumed=114.2270704005161, userId=1), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=1)], 13=[DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=13)], 14=[DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=14)], 15=[DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=15)]}
usage-service      | 2026-10-05 16:21:40.382 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 16
usage-service      | 2026-10-05 16:21:40.405 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 13
usage-service      | 2026-10-05 16:21:40.446 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 14
usage-service      | 2026-10-05 16:21:40.458 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 15
usage-service      | 2026-10-05 16:21:40.458 [] INFO  c.h.u.service.UsageService - User Threshold Map: {1=25.0}
usage-service      | 2026-10-05 16:21:40.458 [] INFO  c.h.u.service.UsageService - ALERT: User ID 1 has exceeded the energy threshold! Total Consumption: 115.2270704005161, Threshold: 25.0
usage-service      | 2026-10-05 16:21:50.401 [] INFO  c.h.u.service.UsageService - Aggregated device energies over the past hour: [DeviceEnergy(deviceId=1, energyConsumed=114.2270704005161, userId=null), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=null)]
usage-service      | 2026-10-05 16:21:50.531 [] INFO  c.h.u.service.UsageService - User-Device Energy Map: {16=[DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=16)], 1=[DeviceEnergy(deviceId=1, energyConsumed=114.2270704005161, userId=1), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=1)], 13=[DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=13)], 14=[DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=14)], 15=[DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=15)]}
usage-service      | 2026-10-05 16:21:50.551 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 16
usage-service      | 2026-10-05 16:21:50.654 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 13
usage-service      | 2026-10-05 16:21:50.669 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 14
usage-service      | 2026-10-05 16:21:50.681 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 15
usage-service      | 2026-10-05 16:21:50.681 [] INFO  c.h.u.service.UsageService - User Threshold Map: {1=25.0}
usage-service      | 2026-10-05 16:21:50.681 [] INFO  c.h.u.service.UsageService - ALERT: User ID 1 has exceeded the energy threshold! Total Consumption: 115.2270704005161, Threshold: 25.0
usage-service      | 2026-10-05 16:22:00.198 [] INFO  c.h.u.service.UsageService - Aggregated device energies over the past hour: [DeviceEnergy(deviceId=1, energyConsumed=114.2270704005161, userId=null), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=null)]
usage-service      | 2026-10-05 16:22:00.348 [] INFO  c.h.u.service.UsageService - User-Device Energy Map: {16=[DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=16)], 1=[DeviceEnergy(deviceId=1, energyConsumed=114.2270704005161, userId=1), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=1)], 13=[DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=13)], 14=[DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=14)], 15=[DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=15)]}
usage-service      | 2026-10-05 16:22:00.371 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 16
usage-service      | 2026-10-05 16:22:00.402 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 13
usage-service      | 2026-10-05 16:22:00.415 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 14
usage-service      | 2026-10-05 16:22:00.425 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 15
usage-service      | 2026-10-05 16:22:00.425 [] INFO  c.h.u.service.UsageService - User Threshold Map: {1=25.0}
usage-service      | 2026-10-05 16:22:00.425 [] INFO  c.h.u.service.UsageService - ALERT: User ID 1 has exceeded the energy threshold! Total Consumption: 115.2270704005161, Threshold: 25.0
usage-service      | 2026-10-05 16:22:10.187 [] INFO  c.h.u.service.UsageService - Aggregated device energies over the past hour: [DeviceEnergy(deviceId=1, energyConsumed=114.2270704005161, userId=null), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=null)]
usage-service      | 2026-10-05 16:22:10.312 [] INFO  c.h.u.service.UsageService - User-Device Energy Map: {16=[DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=16)], 1=[DeviceEnergy(deviceId=1, energyConsumed=114.2270704005161, userId=1), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=1)], 13=[DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=13)], 14=[DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=14)], 15=[DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=15)]}
usage-service      | 2026-10-05 16:22:10.338 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 16
usage-service      | 2026-10-05 16:22:10.359 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 13
usage-service      | 2026-10-05 16:22:10.371 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 14
usage-service      | 2026-10-05 16:22:10.384 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 15
usage-service      | 2026-10-05 16:22:10.384 [] INFO  c.h.u.service.UsageService - User Threshold Map: {1=25.0}
usage-service      | 2026-10-05 16:22:10.385 [] INFO  c.h.u.service.UsageService - ALERT: User ID 1 has exceeded the energy threshold! Total Consumption: 115.2270704005161, Threshold: 25.0
usage-service      | 2026-10-05 16:22:20.555 [] INFO  c.h.u.service.UsageService - Aggregated device energies over the past hour: [DeviceEnergy(deviceId=1, energyConsumed=114.5370704005161, userId=null), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=null)]
usage-service      | 2026-10-05 16:22:21.088 [] INFO  c.h.u.service.UsageService - User-Device Energy Map: {16=[DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=16)], 1=[DeviceEnergy(deviceId=1, energyConsumed=114.5370704005161, userId=1), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=1)], 13=[DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=13)], 14=[DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=14)], 15=[DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=15)]}
usage-service      | 2026-10-05 16:22:21.128 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 16
usage-service      | 2026-10-05 16:22:21.193 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 13
usage-service      | 2026-10-05 16:22:21.222 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 14
usage-service      | 2026-10-05 16:22:21.255 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 15
usage-service      | 2026-10-05 16:22:21.255 [] INFO  c.h.u.service.UsageService - User Threshold Map: {1=25.0}
usage-service      | 2026-10-05 16:22:21.256 [] INFO  c.h.u.service.UsageService - ALERT: User ID 1 has exceeded the energy threshold! Total Consumption: 115.5370704005161, Threshold: 25.0
usage-service      | 2026-10-05 16:22:30.144 [] INFO  c.h.u.service.UsageService - Aggregated device energies over the past hour: [DeviceEnergy(deviceId=1, energyConsumed=114.5370704005161, userId=null), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=null)]
usage-service      | 2026-10-05 16:22:30.276 [] INFO  c.h.u.service.UsageService - User-Device Energy Map: {16=[DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=16)], 1=[DeviceEnergy(deviceId=1, energyConsumed=114.5370704005161, userId=1), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=1)], 13=[DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=13)], 14=[DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=14)], 15=[DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=15)]}
usage-service      | 2026-10-05 16:22:30.292 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 16
usage-service      | 2026-10-05 16:22:30.314 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 13
usage-service      | 2026-10-05 16:22:30.324 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 14
usage-service      | 2026-10-05 16:22:30.333 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 15
usage-service      | 2026-10-05 16:22:30.333 [] INFO  c.h.u.service.UsageService - User Threshold Map: {1=25.0}
usage-service      | 2026-10-05 16:22:30.333 [] INFO  c.h.u.service.UsageService - ALERT: User ID 1 has exceeded the energy threshold! Total Consumption: 115.5370704005161, Threshold: 25.0
usage-service      | 2026-10-05 16:22:40.139 [] INFO  c.h.u.service.UsageService - Aggregated device energies over the past hour: [DeviceEnergy(deviceId=1, energyConsumed=114.5370704005161, userId=null), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=null)]
usage-service      | 2026-10-05 16:22:40.297 [] INFO  c.h.u.service.UsageService - User-Device Energy Map: {16=[DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=16)], 1=[DeviceEnergy(deviceId=1, energyConsumed=114.5370704005161, userId=1), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=1)], 13=[DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=13)], 14=[DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=14)], 15=[DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=15)]}
usage-service      | 2026-10-05 16:22:40.318 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 16
usage-service      | 2026-10-05 16:22:40.342 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 13
usage-service      | 2026-10-05 16:22:40.356 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 14
usage-service      | 2026-10-05 16:22:40.366 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 15
usage-service      | 2026-10-05 16:22:40.366 [] INFO  c.h.u.service.UsageService - User Threshold Map: {1=25.0}
usage-service      | 2026-10-05 16:22:40.366 [] INFO  c.h.u.service.UsageService - ALERT: User ID 1 has exceeded the energy threshold! Total Consumption: 115.5370704005161, Threshold: 25.0
usage-service      | 2026-10-05 16:22:50.140 [] INFO  c.h.u.service.UsageService - Aggregated device energies over the past hour: [DeviceEnergy(deviceId=1, energyConsumed=114.5370704005161, userId=null), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=null)]
usage-service      | 2026-10-05 16:22:50.276 [] INFO  c.h.u.service.UsageService - User-Device Energy Map: {16=[DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=16)], 1=[DeviceEnergy(deviceId=1, energyConsumed=114.5370704005161, userId=1), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=1)], 13=[DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=13)], 14=[DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=14)], 15=[DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=15)]}
usage-service      | 2026-10-05 16:22:50.297 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 16
usage-service      | 2026-10-05 16:22:50.324 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 13
usage-service      | 2026-10-05 16:22:50.335 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 14
usage-service      | 2026-10-05 16:22:50.344 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 15
usage-service      | 2026-10-05 16:22:50.346 [] INFO  c.h.u.service.UsageService - User Threshold Map: {1=25.0}
usage-service      | 2026-10-05 16:22:50.346 [] INFO  c.h.u.service.UsageService - ALERT: User ID 1 has exceeded the energy threshold! Total Consumption: 115.5370704005161, Threshold: 25.0
usage-service      | 2026-10-05 16:23:00.152 [] INFO  c.h.u.service.UsageService - Aggregated device energies over the past hour: [DeviceEnergy(deviceId=1, energyConsumed=114.5370704005161, userId=null), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=null), DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=null), DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=null)]
usage-service      | 2026-10-05 16:23:00.320 [] INFO  c.h.u.service.UsageService - User-Device Energy Map: {16=[DeviceEnergy(deviceId=315, energyConsumed=1.0, userId=16)], 1=[DeviceEnergy(deviceId=1, energyConsumed=114.5370704005161, userId=1), DeviceEnergy(deviceId=2, energyConsumed=1.0, userId=1)], 13=[DeviceEnergy(deviceId=312, energyConsumed=1.5, userId=13)], 14=[DeviceEnergy(deviceId=313, energyConsumed=1.0, userId=14)], 15=[DeviceEnergy(deviceId=314, energyConsumed=1.5, userId=15)]}
usage-service      | 2026-10-05 16:23:00.351 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 16
usage-service      | 2026-10-05 16:23:00.382 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 13
usage-service      | 2026-10-05 16:23:00.397 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 14
usage-service      | 2026-10-05 16:23:00.411 [] WARN  c.h.u.service.UsageService - User not found or alerting disabled for ID: 15
usage-service      | 2026-10-05 16:23:00.412 [] INFO  c.h.u.service.UsageService - User Threshold Map: {1=25.0}
usage-service      | 2026-10-05 16:23:00.412 [] INFO  c.h.u.service.UsageService - ALERT: User ID 1 has exceeded the energy threshold! Total Consumption: 115.5370704005161, Threshold: 25.0
ingestion-service  | 2026-10-05 16:19:00.048 [k6-4-32] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.24796505637860294, timestamp=2026-10-05T16:19:00.032Z]
ingestion-service  | 2026-10-05 16:19:00.155 [k6-7-33] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.27335739598813535, timestamp=2026-10-05T16:19:00.140Z]
ingestion-service  | 2026-10-05 16:19:00.261 [k6-3-33] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2684299530225246, timestamp=2026-10-05T16:19:00.248Z]
ingestion-service  | 2026-10-05 16:19:00.373 [k6-8-33] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.22950127902331624, timestamp=2026-10-05T16:19:00.357Z]
ingestion-service  | 2026-10-05 16:19:00.473 [k6-1-33] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2981253898090152, timestamp=2026-10-05T16:19:00.464Z]
ingestion-service  | 2026-10-05 16:19:00.589 [k6-5-33] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.29910542820528585, timestamp=2026-10-05T16:19:00.573Z]
ingestion-service  | 2026-10-05 16:19:00.736 [k6-10-33] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.23853349619064695, timestamp=2026-10-05T16:19:00.679Z]
ingestion-service  | 2026-10-05 16:19:00.797 [k6-2-33] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.25286712065125605, timestamp=2026-10-05T16:19:00.786Z]
ingestion-service  | 2026-10-05 16:19:00.905 [k6-9-33] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2347374921981661, timestamp=2026-10-05T16:19:00.893Z]
ingestion-service  | 2026-10-05 16:19:01.012 [k6-6-33] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.27017822497827226, timestamp=2026-10-05T16:19:01Z]
ingestion-service  | 2026-10-05 16:19:01.117 [k6-4-33] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.29510994496042814, timestamp=2026-10-05T16:19:01.106Z]
ingestion-service  | 2026-10-05 16:19:01.224 [k6-7-34] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.27581068279229853, timestamp=2026-10-05T16:19:01.213Z]
ingestion-service  | 2026-10-05 16:19:01.330 [k6-3-34] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.22197240362877219, timestamp=2026-10-05T16:19:01.318Z]
ingestion-service  | 2026-10-05 16:19:01.438 [k6-8-34] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.26852346400121047, timestamp=2026-10-05T16:19:01.425Z]
ingestion-service  | 2026-10-05 16:19:01.540 [k6-1-34] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.21262362071422494, timestamp=2026-10-05T16:19:01.530Z]
ingestion-service  | 2026-10-05 16:19:01.645 [k6-5-34] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.21876090700879186, timestamp=2026-10-05T16:19:01.636Z]
ingestion-service  | 2026-10-05 16:19:01.749 [k6-10-34] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.24240367821226239, timestamp=2026-10-05T16:19:01.741Z]
ingestion-service  | 2026-10-05 16:19:01.856 [k6-2-34] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2940897257115568, timestamp=2026-10-05T16:19:01.846Z]
ingestion-service  | 2026-10-05 16:19:01.959 [k6-9-34] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2383120610340994, timestamp=2026-10-05T16:19:01.951Z]
ingestion-service  | 2026-10-05 16:19:02.064 [k6-6-34] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2899471777114833, timestamp=2026-10-05T16:19:02.055Z]
ingestion-service  | 2026-10-05 16:19:02.172 [k6-4-34] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2008596982196363, timestamp=2026-10-05T16:19:02.160Z]
ingestion-service  | 2026-10-05 16:19:02.275 [k6-7-35] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.28682308764960013, timestamp=2026-10-05T16:19:02.264Z]
ingestion-service  | 2026-10-05 16:19:02.381 [k6-3-35] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.23885756946665085, timestamp=2026-10-05T16:19:02.369Z]
ingestion-service  | 2026-10-05 16:19:02.485 [k6-8-35] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2079160586653319, timestamp=2026-10-05T16:19:02.473Z]
ingestion-service  | 2026-10-05 16:19:02.587 [k6-1-35] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.21574683230987432, timestamp=2026-10-05T16:19:02.576Z]
ingestion-service  | 2026-10-05 16:19:02.693 [k6-5-35] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.27070942566595013, timestamp=2026-10-05T16:19:02.680Z]
ingestion-service  | 2026-10-05 16:19:02.804 [k6-10-35] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.27941108367167117, timestamp=2026-10-05T16:19:02.784Z]
ingestion-service  | 2026-10-05 16:19:02.907 [k6-2-35] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2292285894744114, timestamp=2026-10-05T16:19:02.887Z]
ingestion-service  | 2026-10-05 16:19:03.005 [k6-9-35] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.20862836779600155, timestamp=2026-10-05T16:19:02.990Z]
ingestion-service  | 2026-10-05 16:19:03.105 [k6-6-35] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.22503133978751488, timestamp=2026-10-05T16:19:03.093Z]
ingestion-service  | 2026-10-05 16:19:03.210 [k6-4-35] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.21153287206143412, timestamp=2026-10-05T16:19:03.195Z]
ingestion-service  | 2026-10-05 16:19:03.311 [k6-7-36] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.21722977606048602, timestamp=2026-10-05T16:19:03.297Z]
ingestion-service  | 2026-10-05 16:19:03.415 [k6-3-36] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2882729092094918, timestamp=2026-10-05T16:19:03.400Z]
ingestion-service  | 2026-10-05 16:19:03.516 [k6-8-36] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2583954427583888, timestamp=2026-10-05T16:19:03.502Z]
ingestion-service  | 2026-10-05 16:19:03.620 [k6-1-36] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.23815558649299484, timestamp=2026-10-05T16:19:03.604Z]
ingestion-service  | 2026-10-05 16:19:03.788 [k6-5-36] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2782639668474053, timestamp=2026-10-05T16:19:03.706Z]
ingestion-service  | 2026-10-05 16:19:03.835 [k6-10-36] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.22721307505760518, timestamp=2026-10-05T16:19:03.808Z]
ingestion-service  | 2026-10-05 16:19:03.922 [k6-2-36] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.22463494130141906, timestamp=2026-10-05T16:19:03.910Z]
ingestion-service  | 2026-10-05 16:19:04.030 [k6-9-36] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.289067491897244, timestamp=2026-10-05T16:19:04.011Z]
ingestion-service  | 2026-10-05 16:19:04.134 [k6-6-36] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2552060651280811, timestamp=2026-10-05T16:19:04.112Z]
ingestion-service  | 2026-10-05 16:19:04.228 [k6-4-36] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2999147604889481, timestamp=2026-10-05T16:19:04.213Z]
ingestion-service  | 2026-10-05 16:19:04.337 [k6-7-37] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2865342708614904, timestamp=2026-10-05T16:19:04.313Z]
ingestion-service  | 2026-10-05 16:19:04.429 [k6-3-37] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2932767656746608, timestamp=2026-10-05T16:19:04.414Z]
ingestion-service  | 2026-10-05 16:19:04.529 [k6-8-37] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.24401331011746633, timestamp=2026-10-05T16:19:04.514Z]
ingestion-service  | 2026-10-05 16:19:04.647 [k6-1-37] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.21953812122785507, timestamp=2026-10-05T16:19:04.615Z]
ingestion-service  | 2026-10-05 16:19:04.733 [k6-5-37] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.21355695586737838, timestamp=2026-10-05T16:19:04.715Z]
ingestion-service  | 2026-10-05 16:19:04.826 [k6-10-37] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.22783045436844138, timestamp=2026-10-05T16:19:04.815Z]
ingestion-service  | 2026-10-05 16:19:04.924 [k6-2-37] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2620329388677533, timestamp=2026-10-05T16:19:04.916Z]
ingestion-service  | 2026-10-05 16:19:05.038 [k6-9-37] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.21382450038929537, timestamp=2026-10-05T16:19:05.017Z]
ingestion-service  | 2026-10-05 16:19:05.134 [k6-6-37] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.29259629093157075, timestamp=2026-10-05T16:19:05.120Z]
ingestion-service  | 2026-10-05 16:19:05.233 [k6-4-37] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2831685080019683, timestamp=2026-10-05T16:19:05.223Z]
ingestion-service  | 2026-10-05 16:19:05.336 [k6-7-38] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2250707668806256, timestamp=2026-10-05T16:19:05.328Z]
ingestion-service  | 2026-10-05 16:19:05.446 [k6-3-38] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.22907566413049618, timestamp=2026-10-05T16:19:05.432Z]
ingestion-service  | 2026-10-05 16:19:05.547 [k6-8-38] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.219319326145632, timestamp=2026-10-05T16:19:05.537Z]
ingestion-service  | 2026-10-05 16:19:05.656 [k6-1-38] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2764532815519335, timestamp=2026-10-05T16:19:05.643Z]
ingestion-service  | 2026-10-05 16:19:05.783 [k6-5-38] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.24131217550093775, timestamp=2026-10-05T16:19:05.750Z]
ingestion-service  | 2026-10-05 16:19:05.874 [k6-10-38] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2863652164250726, timestamp=2026-10-05T16:19:05.858Z]
ingestion-service  | 2026-10-05 16:19:06.069 [k6-2-38] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.26929389898747425, timestamp=2026-10-05T16:19:05.966Z]
ingestion-service  | 2026-10-05 16:19:06.103 [k6-9-38] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.21500452312523943, timestamp=2026-10-05T16:19:06.076Z]
ingestion-service  | 2026-10-05 16:19:06.199 [k6-6-38] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.26967086941616186, timestamp=2026-10-05T16:19:06.186Z]
ingestion-service  | 2026-10-05 16:19:06.308 [k6-4-38] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2306868031920724, timestamp=2026-10-05T16:19:06.299Z]
ingestion-service  | 2026-10-05 16:19:06.421 [k6-7-39] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.26246989729152737, timestamp=2026-10-05T16:19:06.411Z]
ingestion-service  | 2026-10-05 16:19:06.534 [k6-3-39] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.21383818890577083, timestamp=2026-10-05T16:19:06.523Z]
ingestion-service  | 2026-10-05 16:19:06.650 [k6-8-39] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2412936027043345, timestamp=2026-10-05T16:19:06.638Z]
ingestion-service  | 2026-10-05 16:19:06.767 [k6-1-39] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.24490687222733531, timestamp=2026-10-05T16:19:06.753Z]
ingestion-service  | 2026-10-05 16:19:06.880 [k6-5-39] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.24382225730750562, timestamp=2026-10-05T16:19:06.870Z]
ingestion-service  | 2026-10-05 16:19:06.999 [k6-10-39] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.25205286145726147, timestamp=2026-10-05T16:19:06.987Z]
ingestion-service  | 2026-10-05 16:19:07.115 [k6-2-39] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.281956935523483, timestamp=2026-10-05T16:19:07.105Z]
ingestion-service  | 2026-10-05 16:19:07.234 [k6-9-39] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.21989400930485262, timestamp=2026-10-05T16:19:07.225Z]
ingestion-service  | 2026-10-05 16:19:07.356 [k6-6-39] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.22827261558435935, timestamp=2026-10-05T16:19:07.346Z]
ingestion-service  | 2026-10-05 16:19:07.476 [k6-4-39] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2275881990892843, timestamp=2026-10-05T16:19:07.467Z]
ingestion-service  | 2026-10-05 16:19:07.606 [k6-7-40] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.24466799621956564, timestamp=2026-10-05T16:19:07.590Z]
ingestion-service  | 2026-10-05 16:19:07.762 [k6-3-40] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.23900709911191825, timestamp=2026-10-05T16:19:07.715Z]
ingestion-service  | 2026-10-05 16:19:07.853 [k6-8-40] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.22156429369887048, timestamp=2026-10-05T16:19:07.840Z]
ingestion-service  | 2026-10-05 16:19:07.978 [k6-1-40] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.21292972663094925, timestamp=2026-10-05T16:19:07.967Z]
ingestion-service  | 2026-10-05 16:19:08.109 [k6-5-40] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2305432013595402, timestamp=2026-10-05T16:19:08.095Z]
ingestion-service  | 2026-10-05 16:19:08.240 [k6-10-40] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2856659948248633, timestamp=2026-10-05T16:19:08.226Z]
ingestion-service  | 2026-10-05 16:19:08.372 [k6-2-40] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.20771960643454843, timestamp=2026-10-05T16:19:08.357Z]
ingestion-service  | 2026-10-05 16:19:08.516 [k6-9-40] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.25418608347988597, timestamp=2026-10-05T16:19:08.492Z]
ingestion-service  | 2026-10-05 16:19:08.640 [k6-6-40] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.20162736457365404, timestamp=2026-10-05T16:19:08.624Z]
ingestion-service  | 2026-10-05 16:19:08.801 [k6-4-40] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2904684596787651, timestamp=2026-10-05T16:19:08.762Z]
ingestion-service  | 2026-10-05 16:19:08.961 [k6-7-41] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.22271978892483474, timestamp=2026-10-05T16:19:08.898Z]
ingestion-service  | 2026-10-05 16:19:09.068 [k6-3-41] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.28326383689560636, timestamp=2026-10-05T16:19:09.039Z]
ingestion-service  | 2026-10-05 16:19:09.225 [k6-8-41] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2164689212895872, timestamp=2026-10-05T16:19:09.183Z]
ingestion-service  | 2026-10-05 16:19:09.351 [k6-1-41] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.20835825379374226, timestamp=2026-10-05T16:19:09.323Z]
ingestion-service  | 2026-10-05 16:19:09.544 [k6-5-41] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.27833575920041037, timestamp=2026-10-05T16:19:09.468Z]
ingestion-service  | 2026-10-05 16:19:09.844 [k6-2-41] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.20687758334428166, timestamp=2026-10-05T16:19:09.771Z]
ingestion-service  | 2026-10-05 16:19:09.847 [k6-10-41] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2904915752133653, timestamp=2026-10-05T16:19:09.616Z]
ingestion-service  | 2026-10-05 16:19:09.930 [k6-9-41] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2592190947470626, timestamp=2026-10-05T16:19:09.916Z]
ingestion-service  | 2026-10-05 16:19:10.185 [k6-6-41] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.20182814163633286, timestamp=2026-10-05T16:19:10.072Z]
ingestion-service  | 2026-10-05 16:19:10.468 [k6-4-41] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.29233367996397636, timestamp=2026-10-05T16:19:10.242Z]
ingestion-service  | 2026-10-05 16:19:10.474 [k6-7-42] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.26665446173704577, timestamp=2026-10-05T16:19:10.399Z]
ingestion-service  | 2026-10-05 16:19:10.852 [k6-3-42] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.26972980107577943, timestamp=2026-10-05T16:19:10.550Z]
ingestion-service  | 2026-10-05 16:19:10.968 [k6-8-42] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.20273748227296093, timestamp=2026-10-05T16:19:10.724Z]
ingestion-service  | 2026-10-05 16:19:10.993 [k6-1-42] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.21534640142116537, timestamp=2026-10-05T16:19:10.887Z]
ingestion-service  | 2026-10-05 16:19:11.160 [k6-5-42] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.29012424334574494, timestamp=2026-10-05T16:19:11.059Z]
ingestion-service  | 2026-10-05 16:19:11.265 [k6-2-42] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2619377458184372, timestamp=2026-10-05T16:19:11.232Z]
ingestion-service  | 2026-10-05 16:19:11.428 [k6-10-42] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2728278265716485, timestamp=2026-10-05T16:19:11.409Z]
ingestion-service  | 2026-10-05 16:19:11.622 [k6-9-42] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2843809918661915, timestamp=2026-10-05T16:19:11.592Z]
ingestion-service  | 2026-10-05 16:19:11.811 [k6-6-42] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2728444343049581, timestamp=2026-10-05T16:19:11.782Z]
ingestion-service  | 2026-10-05 16:19:12.030 [k6-7-43] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2506158052135226, timestamp=2026-10-05T16:19:11.976Z]
ingestion-service  | 2026-10-05 16:19:12.267 [k6-4-42] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.28222042023401944, timestamp=2026-10-05T16:19:12.176Z]
ingestion-service  | 2026-10-05 16:19:12.404 [k6-3-43] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.29445113903404563, timestamp=2026-10-05T16:19:12.373Z]
ingestion-service  | 2026-10-05 16:19:12.600 [k6-8-43] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.20658238135189097, timestamp=2026-10-05T16:19:12.575Z]
ingestion-service  | 2026-10-05 16:19:12.840 [k6-1-43] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.27436118130769427, timestamp=2026-10-05T16:19:12.795Z]
ingestion-service  | 2026-10-05 16:19:13.060 [k6-5-43] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.24799324829047134, timestamp=2026-10-05T16:19:13.013Z]
ingestion-service  | 2026-10-05 16:19:13.259 [k6-2-43] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.268663225226444, timestamp=2026-10-05T16:19:13.235Z]
ingestion-service  | 2026-10-05 16:19:13.564 [k6-10-43] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2036875118635233, timestamp=2026-10-05T16:19:13.472Z]
ingestion-service  | 2026-10-05 16:19:13.795 [k6-9-43] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.20876292756204204, timestamp=2026-10-05T16:19:13.731Z]
ingestion-service  | 2026-10-05 16:19:14.121 [k6-6-43] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2164181056925472, timestamp=2026-10-05T16:19:13.987Z]
ingestion-service  | 2026-10-05 16:19:14.297 [k6-7-44] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.25802942449526634, timestamp=2026-10-05T16:19:14.254Z]
ingestion-service     | 2026-10-05 16:19:14.763 [k6-4-43] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2620146787773616, timestamp=2026-10-05T16:19:14.530Z]
ingestion-service     | 2026-10-05 16:19:14.887 [k6-3-44] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.24324464675607882, timestamp=2026-10-05T16:19:14.824Z]
ingestion-service     | 2026-10-05 16:19:15.243 [k6-8-44] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.21785623180487146, timestamp=2026-10-05T16:19:15.149Z]
ingestion-service     | 2026-10-05 16:19:15.532 [k6-1-44] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2969817222034185, timestamp=2026-10-05T16:19:15.475Z]
ingestion-service     | 2026-10-05 16:19:15.933 [k6-5-44] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.20615122480411266, timestamp=2026-10-05T16:19:15.856Z]
ingestion-service     | 2026-10-05 16:19:16.264 [k6-2-44] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.28518188342665773, timestamp=2026-10-05T16:19:16.250Z]
ingestion-service     | 2026-10-05 16:19:16.722 [k6-10-44] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.23900486355453618, timestamp=2026-10-05T16:19:16.714Z]
ingestion-service     | 2026-10-05 16:19:17.324 [k6-9-44] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.25620031205240046, timestamp=2026-10-05T16:19:17.273Z]
ingestion-service     | 2026-10-05 16:19:18.073 [k6-6-44] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.2554729151212965, timestamp=2026-10-05T16:19:18.003Z]
ingestion-service     | 2026-10-05 16:19:19.775 [k6-7-45] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.22499386092324464, timestamp=2026-10-05T16:19:19.721Z]
ingestion-service     | 2026-10-05 16:20:46.923 [22a3aa41-c3f9-40d0-889b-80c2dbeccded] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.31, timestamp=2026-10-05T16:20:46.533863300Z]
ingestion-service     | 2026-10-05 16:22:19.457 [5e445c26-1862-4d67-96a8-b46f87c6134a] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.31, timestamp=2026-10-05T16:22:19.190335100Z]
ingestion-service     | 2026-10-05 16:23:06.650 [5b7df8ec-a67e-4bb3-9d49-9a9a725465f0] INFO  c.h.i.service.IngestionService - Ingested Energy Usage Event: EnergyUsageEvent[deviceId=1, energyConsumed=0.31, timestamp=2026-10-05T16:23:06.346347700Z]
alert-service      | 2026-10-05 16:19:01.305 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:01.435 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:01.572 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:19:01,434 INFO ml_inference.kafka Published anomaly result for device 1
alert-service         | 2026-10-05 16:19:01.679 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:01.784 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:01.887 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:01.987 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:02.078 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:02.184 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:02.316 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:02.438 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:02.566 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:02.722 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:19:01,571 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:01,677 INFO ml_inference.kafka Published anomaly result for device 1
alert-service         | 2026-10-05 16:19:02.890 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:03.062 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:03.228 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:03.400 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:03.585 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:19:01,783 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:01,885 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:01,986 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:02,076 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:02,182 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:02,315 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:02,437 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:02,565 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:02,721 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:02,892 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:03,060 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:03,228 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:03,399 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:03,584 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:03,741 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:03,931 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:04,095 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:04,284 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:04,470 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:04,639 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:04,794 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:04,929 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:05,054 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:05,197 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:05,306 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:05,418 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:05,547 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:05,675 INFO ml_inference.kafka Published anomaly result for device 1
alert-service         | 2026-10-05 16:19:03.742 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:03.936 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:04.099 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:04.287 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:04.472 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:19:05,883 INFO ml_inference.kafka Published anomaly result for device 1
alert-service         | 2026-10-05 16:19:04.641 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:04.799 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:19:06,032 INFO ml_inference.kafka Published anomaly result for device 1
alert-service         | 2026-10-05 16:19:04.932 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:05.056 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:05.198 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:05.308 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:05.420 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:05.550 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:05.677 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:05.883 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:06.035 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:06.183 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:06.296 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:06.401 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:06.515 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:06.627 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:19:06,182 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:06,294 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:06,400 INFO ml_inference.kafka Published anomaly result for device 1
alert-service         | 2026-10-05 16:19:06.752 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:06.883 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:06.997 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:07.106 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:19:06,512 INFO ml_inference.kafka Published anomaly result for device 1
alert-service         | 2026-10-05 16:19:07.206 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:07.314 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:07.419 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:07.525 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:07.644 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:19:06,624 INFO ml_inference.kafka Published anomaly result for device 1
alert-service         | 2026-10-05 16:19:07.782 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:19:06,750 INFO ml_inference.kafka Published anomaly result for device 1
alert-service         | 2026-10-05 16:19:07.915 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:19:06,879 INFO ml_inference.kafka Published anomaly result for device 1
alert-service         | 2026-10-05 16:19:08.046 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:19:06,994 INFO ml_inference.kafka Published anomaly result for device 1
alert-service         | 2026-10-05 16:19:08.195 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:19:07,105 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:07,205 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:07,312 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:07,418 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:07,524 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:07,642 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | INFO:     172.20.0.17:34110 - "GET /metrics HTTP/1.1" 200 OK
ml-inference-service  | 2026-10-05 16:19:07,780 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:07,913 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:08,045 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:08,194 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:08,323 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:08,489 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:08,688 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:08,876 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:09,107 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:09,332 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:09,483 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:09,686 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:09,922 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:10,067 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:10,234 INFO ml_inference.kafka Published anomaly result for device 1
alert-service         | 2026-10-05 16:19:08.325 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:08.492 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:08.690 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:08.878 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:09.109 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:09.335 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:09.487 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:09.692 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:09.926 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:10.076 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:10.238 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:10.643 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:11.081 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:11.147 [] INFO  c.h.a.service.AlertService - Suppressed duplicate alert with key 1:HOUSEHOLD:THRESHOLD inside 15 minutes
alert-service         | 2026-10-05 16:19:11.462 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:11.694 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:11.884 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:12.157 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:12.535 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:12.791 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:12.977 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:13.177 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:13.351 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:13.583 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:13.941 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:19:10,637 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:11,075 INFO ml_inference.kafka Published anomaly result for device 1
alert-service         | 2026-10-05 16:19:14.294 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:19:11,457 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:11,689 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:11,878 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:12,148 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:12,534 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:12,790 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:12,974 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:13,173 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:13,348 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:13,579 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:13,928 INFO ml_inference.kafka Published anomaly result for device 1
alert-service         | 2026-10-05 16:19:14.595 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:19:14,288 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:14,574 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:14,835 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:15,024 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:15,200 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:15,371 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:15,588 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:15,763 INFO ml_inference.kafka Published anomaly result for device 1
alert-service         | 2026-10-05 16:19:14.838 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:15.040 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:15.205 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:15.374 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:15.590 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:19:15,927 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:16,082 INFO ml_inference.kafka Published anomaly result for device 1
alert-service         | 2026-10-05 16:19:15.765 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:15.930 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:16.083 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:16.189 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:16.330 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:16.447 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:19:16,188 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:16,327 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:16,445 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:16,549 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:16,652 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:16,764 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:16,866 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:16,986 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:17,117 INFO ml_inference.kafka Published anomaly result for device 1
alert-service         | 2026-10-05 16:19:16.550 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:19:17,222 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:17,345 INFO ml_inference.kafka Published anomaly result for device 1
alert-service         | 2026-10-05 16:19:16.655 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:19:17,457 INFO ml_inference.kafka Published anomaly result for device 1
alert-service         | 2026-10-05 16:19:16.765 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:19:17,580 INFO ml_inference.kafka Published anomaly result for device 1
alert-service         | 2026-10-05 16:19:16.867 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:19:17,689 INFO ml_inference.kafka Published anomaly result for device 1
alert-service         | 2026-10-05 16:19:16.988 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:19:17,821 INFO ml_inference.kafka Published anomaly result for device 1
alert-service         | 2026-10-05 16:19:17.117 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:19:17,940 INFO ml_inference.kafka Published anomaly result for device 1
alert-service         | 2026-10-05 16:19:17.223 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:19:18,059 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:18,184 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:18,286 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:18,384 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:18,486 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:18,593 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:18,713 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:18,822 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:18,946 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:19,071 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:19,200 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:19,307 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:19,415 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:19,513 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:19,617 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:19,723 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:19,851 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:19,983 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:20,156 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:20,291 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:20,430 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | 2026-10-05 16:19:20,586 INFO ml_inference.kafka Published anomaly result for device 1
alert-service         | 2026-10-05 16:19:17.347 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:17.459 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:17.582 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:17.691 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:17.822 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:17.941 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:18.061 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:18.191 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:18.287 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:18.385 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:18.487 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:18.595 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:18.714 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:18.824 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:18.948 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | INFO:     172.20.0.17:44510 - "GET /metrics HTTP/1.1" 200 OK
ml-inference-service  | INFO:     172.20.0.17:46954 - "GET /metrics HTTP/1.1" 200 OK
ml-inference-service  | INFO:     172.20.0.17:53782 - "GET /metrics HTTP/1.1" 200 OK
ml-inference-service  | INFO:     172.20.0.17:53652 - "GET /metrics HTTP/1.1" 200 OK
ml-inference-service  | INFO:     172.20.0.17:51974 - "GET /metrics HTTP/1.1" 200 OK
ml-inference-service  | INFO:     172.20.0.17:51504 - "GET /metrics HTTP/1.1" 200 OK
ml-inference-service  | 2026-10-05 16:20:47,820 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | INFO:     172.20.0.17:37358 - "GET /metrics HTTP/1.1" 200 OK
ml-inference-service  | INFO:     172.20.0.17:50214 - "GET /metrics HTTP/1.1" 200 OK
ml-inference-service  | INFO:     172.20.0.17:39018 - "GET /metrics HTTP/1.1" 200 OK
ml-inference-service  | INFO:     172.20.0.17:49180 - "GET /metrics HTTP/1.1" 200 OK
ml-inference-service  | INFO:     172.20.0.17:48344 - "GET /metrics HTTP/1.1" 200 OK
ml-inference-service  | INFO:     172.20.0.17:57238 - "GET /metrics HTTP/1.1" 200 OK
alert-service         | 2026-10-05 16:19:19.076 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:19.205 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:19.309 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:19.416 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:22:20,180 INFO ml_inference.kafka Published anomaly result for device 1
ml-inference-service  | INFO:     172.20.0.17:48312 - "GET /metrics HTTP/1.1" 200 OK
ml-inference-service  | INFO:     172.20.0.17:51850 - "GET /metrics HTTP/1.1" 200 OK
ml-inference-service  | INFO:     172.20.0.17:40202 - "GET /metrics HTTP/1.1" 200 OK
ml-inference-service  | INFO:     Shutting down
alert-service         | 2026-10-05 16:19:19.514 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:19.618 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:19.724 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | INFO:     Waiting for application shutdown.
ml-inference-service  | 2026-10-05 16:23:02,205 INFO kafka.coordinator Stopping heartbeat thread
alert-service         | 2026-10-05 16:19:19.853 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:19.984 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:20.165 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:20.294 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:20.434 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:19:20.529 [] INFO  c.h.a.service.AlertService - Suppressed duplicate alert with key 1:HOUSEHOLD:THRESHOLD inside 15 minutes
alert-service         | 2026-10-05 16:19:20.587 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
ml-inference-service  | 2026-10-05 16:23:02,390 INFO kafka.conn <BrokerConnection node_id=1 host=kafka:9092 <connected> [IPv4 ('172.20.0.8', 9092)]>: Closing connection. 
ml-inference-service  | 2026-10-05 16:23:02,485 INFO kafka.coordinator Leaving consumer group (ml-inference-service).
ml-inference-service  | 2026-10-05 16:23:02,568 INFO kafka.conn <BrokerConnection node_id=coordinator-1 host=kafka:9092 <connected> [IPv4 ('172.20.0.8', 9092)]>: Closing connection. 
ml-inference-service  | 2026-10-05 16:23:02,570 INFO kafka.conn <BrokerConnection node_id=1 host=kafka:9092 <connected> [IPv4 ('172.20.0.8', 9092)]>: Closing connection. 
ml-inference-service  | INFO:     Application shutdown complete.
ml-inference-service  | INFO:     Finished server process [1]
alert-service         | 2026-10-05 16:19:30.534 [] INFO  c.h.a.service.AlertService - Suppressed duplicate alert with key 1:HOUSEHOLD:THRESHOLD inside 15 minutes
alert-service         | 2026-10-05 16:19:40.580 [] INFO  c.h.a.service.AlertService - Suppressed duplicate alert with key 1:HOUSEHOLD:THRESHOLD inside 15 minutes
alert-service         | 2026-10-05 16:19:50.474 [] INFO  c.h.a.service.AlertService - Suppressed duplicate alert with key 1:HOUSEHOLD:THRESHOLD inside 15 minutes
alert-service         | 2026-10-05 16:20:00.577 [] INFO  c.h.a.service.AlertService - Suppressed duplicate alert with key 1:HOUSEHOLD:THRESHOLD inside 15 minutes
alert-service         | 2026-10-05 16:20:10.454 [] INFO  c.h.a.service.AlertService - Suppressed duplicate alert with key 1:HOUSEHOLD:THRESHOLD inside 15 minutes
alert-service         | 2026-10-05 16:20:20.462 [] INFO  c.h.a.service.AlertService - Suppressed duplicate alert with key 1:HOUSEHOLD:THRESHOLD inside 15 minutes
alert-service         | 2026-10-05 16:20:30.489 [] INFO  c.h.a.service.AlertService - Suppressed duplicate alert with key 1:HOUSEHOLD:THRESHOLD inside 15 minutes
alert-service         | 2026-10-05 16:20:43.015 [] INFO  c.h.a.service.AlertService - Suppressed duplicate alert with key 1:HOUSEHOLD:THRESHOLD inside 15 minutes
alert-service         | 2026-10-05 16:20:47.834 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:20:51.060 [] INFO  c.h.a.service.AlertService - Suppressed duplicate alert with key 1:HOUSEHOLD:THRESHOLD inside 15 minutes
alert-service         | 2026-10-05 16:21:00.445 [] INFO  c.h.a.service.AlertService - Suppressed duplicate alert with key 1:HOUSEHOLD:THRESHOLD inside 15 minutes
alert-service         | 2026-10-05 16:21:10.489 [] INFO  c.h.a.service.AlertService - Suppressed duplicate alert with key 1:HOUSEHOLD:THRESHOLD inside 15 minutes
alert-service         | 2026-10-05 16:21:25.486 [] INFO  c.h.a.service.AlertService - Suppressed duplicate alert with key 1:HOUSEHOLD:THRESHOLD inside 15 minutes
alert-service         | 2026-10-05 16:21:30.490 [] INFO  c.h.a.service.AlertService - Suppressed duplicate alert with key 1:HOUSEHOLD:THRESHOLD inside 15 minutes
alert-service         | 2026-10-05 16:21:40.483 [] INFO  c.h.a.service.AlertService - Suppressed duplicate alert with key 1:HOUSEHOLD:THRESHOLD inside 15 minutes
alert-service         | 2026-10-05 16:21:50.715 [] INFO  c.h.a.service.AlertService - Suppressed duplicate alert with key 1:HOUSEHOLD:THRESHOLD inside 15 minutes
alert-service         | 2026-10-05 16:22:00.480 [] INFO  c.h.a.service.AlertService - Suppressed duplicate alert with key 1:HOUSEHOLD:THRESHOLD inside 15 minutes
alert-service         | 2026-10-05 16:22:10.423 [] INFO  c.h.a.service.AlertService - Suppressed duplicate alert with key 1:HOUSEHOLD:THRESHOLD inside 15 minutes
alert-service         | 2026-10-05 16:22:20.238 [] INFO  c.h.a.service.AlertService - ML result for device 1 is normal; no alert is created
alert-service         | 2026-10-05 16:22:21.382 [] INFO  c.h.a.service.AlertService - Suppressed duplicate alert with key 1:HOUSEHOLD:THRESHOLD inside 15 minutes
alert-service         | 2026-10-05 16:22:30.382 [] INFO  c.h.a.service.AlertService - Suppressed duplicate alert with key 1:HOUSEHOLD:THRESHOLD inside 15 minutes
alert-service         | 2026-10-05 16:22:40.396 [] INFO  c.h.a.service.AlertService - Suppressed duplicate alert with key 1:HOUSEHOLD:THRESHOLD inside 15 minutes
alert-service         | 2026-10-05 16:22:50.396 [] INFO  c.h.a.service.AlertService - Suppressed duplicate alert with key 1:HOUSEHOLD:THRESHOLD inside 15 minutes
alert-service         | 2026-10-05 16:23:00.457 [] INFO  c.h.a.service.AlertService - Suppressed duplicate alert with key 1:HOUSEHOLD:THRESHOLD inside 15 minutes


## Recovery action
NAME                   IMAGE                                      COMMAND                  SERVICE                CREATED          STATUS         PORTS
ml-inference-service   home-energy-tracker-ml-inference-service   "uvicorn app.main:ap…"   ml-inference-service   46 minutes ago   Up 6 seconds   8090/tcp


Recovery container-state observation finished: 2026-10-05T21:53:15.6005956+05:30; recovered=True
