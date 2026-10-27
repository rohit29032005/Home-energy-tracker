FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /build

COPY pom.xml .
COPY src src
# Unit tests run in the host/CI verification phase. The image-build property
# disables the test-support Maven profile so test-only Kafka/RocksDB artifacts
# are not downloaded while constructing the runtime image.
RUN mvn -B -Ddocker.image.build=true -Dmaven.test.skip=true package

FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY --from=build /build/target/*.jar app.jar

EXPOSE 8085
ENTRYPOINT ["java", "-jar", "app.jar"]
