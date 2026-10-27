package com.hometracker.usage_service.config;

import org.apache.kafka.common.TopicPartition;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.listener.DeadLetterPublishingRecoverer;
import org.springframework.kafka.listener.DefaultErrorHandler;
import org.springframework.util.backoff.FixedBackOff;

/**
 * Bounded recovery for failed InfluxDB writes from the energy-usage listener.
 *
 * A consumed record is retried locally and then published to a same-partition
 * dead-letter topic. The recoverer is configured to fail when its DLT publish
 * fails so a source record is never silently acknowledged because the DLT is
 * unavailable.
 */
@Configuration
public class UsageKafkaErrorHandlingConfig {

    @Bean
    DefaultErrorHandler usageKafkaErrorHandler(
            KafkaTemplate<Object, Object> kafkaTemplate,
            @Value("${usage.kafka.influx.retry-delay-ms:1000}") long retryDelayMillis,
            @Value("${usage.kafka.influx.max-retries:2}") long maxRetries,
            @Value("${usage.kafka.influx.failure-topic-suffix:.DLT}") String failureTopicSuffix) {
        if (retryDelayMillis < 1) {
            throw new IllegalArgumentException("usage.kafka.influx.retry-delay-ms must be positive");
        }
        if (maxRetries < 0) {
            throw new IllegalArgumentException("usage.kafka.influx.max-retries must not be negative");
        }
        if (failureTopicSuffix == null || failureTopicSuffix.isBlank()) {
            throw new IllegalArgumentException("usage.kafka.influx.failure-topic-suffix must not be blank");
        }

        DeadLetterPublishingRecoverer recoverer = new DeadLetterPublishingRecoverer(
                kafkaTemplate,
                (record, exception) -> new TopicPartition(
                        record.topic() + failureTopicSuffix,
                        record.partition()));
        recoverer.setFailIfSendResultIsError(true);

        // FixedBackOff counts retries after the initial listener invocation:
        // default configuration therefore permits one initial attempt plus two
        // retries before delivery to energy-usage.DLT.
        return new DefaultErrorHandler(recoverer, new FixedBackOff(retryDelayMillis, maxRetries));
    }
}
