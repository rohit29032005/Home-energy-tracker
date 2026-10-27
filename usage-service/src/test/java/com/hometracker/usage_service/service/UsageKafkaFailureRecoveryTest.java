package com.hometracker.usage_service.service;

import com.influxdb.client.InfluxDBClient;
import com.influxdb.client.WriteApiBlocking;
import com.hometracker.kafka.event.EnergyUsageEvent;
import org.apache.kafka.clients.consumer.Consumer;
import org.apache.kafka.clients.consumer.ConsumerConfig;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.apache.kafka.clients.consumer.ConsumerRecords;
import org.apache.kafka.common.serialization.ByteArrayDeserializer;
import org.apache.kafka.common.serialization.StringDeserializer;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.kafka.core.DefaultKafkaConsumerFactory;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.test.EmbeddedKafkaBroker;
import org.springframework.kafka.test.context.EmbeddedKafka;
import org.springframework.kafka.test.utils.KafkaTestUtils;
import org.springframework.test.annotation.DirtiesContext;

import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.reset;
import static org.mockito.Mockito.timeout;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

/**
 * Broker-backed contract for the bounded Influx failure policy. This verifies
 * the real Spring Kafka listener/error-handler wiring without Docker.
 */
@SpringBootTest(properties = {
        "spring.kafka.bootstrap-servers=${spring.embedded.kafka.brokers}",
        "spring.kafka.consumer.auto-offset-reset=earliest",
        "spring.kafka.consumer.key-deserializer=org.apache.kafka.common.serialization.StringDeserializer",
        "spring.kafka.consumer.value-deserializer=org.springframework.kafka.support.serializer.JsonDeserializer",
        "spring.kafka.consumer.properties.spring.json.trusted.packages=*",
        "spring.kafka.consumer.properties.spring.json.use.type.headers=false",
        "spring.kafka.consumer.properties.spring.json.value.default.type=com.hometracker.kafka.event.EnergyUsageEvent",
        "spring.kafka.producer.key-serializer=org.apache.kafka.common.serialization.StringSerializer",
        "spring.kafka.producer.value-serializer=org.springframework.kafka.support.serializer.JsonSerializer",
        "spring.kafka.listener.auto-startup=true",
        "spring.task.scheduling.enabled=false",
        "influx.org=hometracker",
        "influx.bucket=usage-bucket",
        "usage.kafka.influx.retry-delay-ms=10",
        "usage.kafka.influx.max-retries=2"
})
@EmbeddedKafka(partitions = 1, topics = {"energy-usage", "energy-usage.DLT"})
@DirtiesContext
class UsageKafkaFailureRecoveryTest {

    @Autowired
    private EmbeddedKafkaBroker embeddedKafka;

    @Autowired
    private KafkaTemplate<Object, Object> kafkaTemplate;

    @MockBean
    private InfluxDBClient influxDBClient;

    @MockBean
    private WriteApiBlocking writeApi;

    @AfterEach
    void cleanMocks() {
        reset(influxDBClient, writeApi);
    }

    @Test
    void routesAnEventToTheSamePartitionDltAfterTheConfiguredInfluxRetries() throws Exception {
        when(influxDBClient.getWriteApiBlocking()).thenReturn(writeApi);
        doThrow(new IllegalStateException("Influx unavailable"))
                .when(writeApi)
                .writePoint(eq("usage-bucket"), eq("hometracker"), any());

        try (Consumer<String, byte[]> dltConsumer = newDltConsumer()) {
            embeddedKafka.consumeFromAnEmbeddedTopic(dltConsumer, "energy-usage.DLT");
            kafkaTemplate.send("energy-usage", reading()).get(10, TimeUnit.SECONDS);

            ConsumerRecord<String, byte[]> record = KafkaTestUtils.getSingleRecord(
                    dltConsumer, "energy-usage.DLT", Duration.ofSeconds(15));

            verify(writeApi, timeout(10_000).times(3))
                    .writePoint(eq("usage-bucket"), eq("hometracker"), any());
            assertTrue(new String(record.value(), StandardCharsets.UTF_8).contains("\"deviceId\":1"));
            assertTrue(record.topic().equals("energy-usage.DLT"));
            assertTrue(record.partition() == 0);
        }
    }

    @Test
    void retriesAndCompletesWithoutPublishingToTheDltWhenInfluxRecovers() throws Exception {
        when(influxDBClient.getWriteApiBlocking()).thenReturn(writeApi);
        doThrow(new IllegalStateException("Transient Influx failure"))
                .doNothing()
                .when(writeApi)
                .writePoint(eq("usage-bucket"), eq("hometracker"), any());

        try (Consumer<String, byte[]> dltConsumer = newLatestDltConsumer()) {
            dltConsumer.subscribe(List.of("energy-usage.DLT"));
            // Establish the assignment before publishing the source record so
            // this observer starts at the DLT's current end offset.
            dltConsumer.poll(Duration.ofMillis(250));

            kafkaTemplate.send("energy-usage", reading()).get(10, TimeUnit.SECONDS);

            verify(writeApi, timeout(10_000).times(2))
                    .writePoint(eq("usage-bucket"), eq("hometracker"), any());
            ConsumerRecords<String, byte[]> dltRecords = dltConsumer.poll(Duration.ofSeconds(2));
            assertTrue(dltRecords.isEmpty(),
                    "a record that succeeds on retry must not be published to the DLT");
        }
    }

    private Consumer<String, byte[]> newDltConsumer() {
        Map<String, Object> properties = KafkaTestUtils.consumerProps(
                "usage-dlt-observer", "false", embeddedKafka);
        properties.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "earliest");
        properties.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class);
        properties.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, ByteArrayDeserializer.class);
        return new DefaultKafkaConsumerFactory<String, byte[]>(properties).createConsumer();
    }

    private Consumer<String, byte[]> newLatestDltConsumer() {
        Map<String, Object> properties = KafkaTestUtils.consumerProps(
                "usage-dlt-recovery-observer", "false", embeddedKafka);
        properties.put(ConsumerConfig.AUTO_OFFSET_RESET_CONFIG, "latest");
        properties.put(ConsumerConfig.KEY_DESERIALIZER_CLASS_CONFIG, StringDeserializer.class);
        properties.put(ConsumerConfig.VALUE_DESERIALIZER_CLASS_CONFIG, ByteArrayDeserializer.class);
        return new DefaultKafkaConsumerFactory<String, byte[]>(properties).createConsumer();
    }

    private static EnergyUsageEvent reading() {
        return EnergyUsageEvent.builder()
                .deviceId(1L)
                .energyConsumed(0.25)
                .timestamp(Instant.parse("2026-01-01T00:00:00Z"))
                .build();
    }
}
