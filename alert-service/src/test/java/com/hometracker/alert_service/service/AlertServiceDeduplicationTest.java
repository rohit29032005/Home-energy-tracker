package com.hometracker.alert_service.service;

import com.hometracker.alert_service.client.AlertContextClient;
import com.hometracker.alert_service.entity.Alert;
import com.hometracker.alert_service.repository.AlertRepository;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.ArgumentCaptor.forClass;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AlertServiceDeduplicationTest {

    @Test
    void createsFirstAlertThenSuppressesSameKeyInsideWindow() {
        EmailService emailService = mock(EmailService.class);
        AlertRepository repository = mock(AlertRepository.class);
        AlertContextClient contextClient = mock(AlertContextClient.class);
        AlertMetrics alertMetrics = mock(AlertMetrics.class);
        AlertService service = new AlertService(emailService, repository, contextClient, alertMetrics, true, 15);
        when(repository.save(any(Alert.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(emailService.sendEmail(any(), any(), any())).thenReturn(true);
        when(repository.findTopByDeduplicationKeyOrderByCreatedAtDesc("1:7:ML_ANOMALY"))
                .thenReturn(Optional.empty())
                .thenReturn(Optional.of(Alert.builder().createdAt(LocalDateTime.now()).build()));

        assertTrue(service.processAlert(1L, 7L, "ML_ANOMALY", "anomaly", 0.4, 0.9, "owner@example.test"));
        assertFalse(service.processAlert(1L, 7L, "ML_ANOMALY", "anomaly", 0.4, 0.9, "owner@example.test"));

        verify(repository, times(2)).save(any(Alert.class));
        verify(emailService, times(1)).sendEmail(eq("owner@example.test"), any(), any());
    }

    @Test
    void keepsDifferentDevicesIndependent() {
        EmailService emailService = mock(EmailService.class);
        AlertRepository repository = mock(AlertRepository.class);
        AlertContextClient contextClient = mock(AlertContextClient.class);
        AlertMetrics alertMetrics = mock(AlertMetrics.class);
        AlertService service = new AlertService(emailService, repository, contextClient, alertMetrics, true, 15);
        when(repository.save(any(Alert.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(emailService.sendEmail(any(), any(), any())).thenReturn(true);
        when(repository.findTopByDeduplicationKeyOrderByCreatedAtDesc(any())).thenReturn(Optional.empty());

        assertTrue(service.processAlert(1L, 7L, "ML_ANOMALY", "a", 0.4, 0.9, "owner@example.test"));
        assertTrue(service.processAlert(1L, 8L, "ML_ANOMALY", "b", 0.4, 0.9, "owner@example.test"));

        verify(emailService, times(2)).sendEmail(any(), any(), any());
    }

    @Test
    void createsNewAlertAfterTheDeduplicationWindow() {
        EmailService emailService = mock(EmailService.class);
        AlertRepository repository = mock(AlertRepository.class);
        AlertContextClient contextClient = mock(AlertContextClient.class);
        AlertMetrics alertMetrics = mock(AlertMetrics.class);
        AlertService service = new AlertService(emailService, repository, contextClient, alertMetrics, true, 15);
        when(repository.save(any(Alert.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(emailService.sendEmail(any(), any(), any())).thenReturn(true);
        when(repository.findTopByDeduplicationKeyOrderByCreatedAtDesc("1:7:ML_ANOMALY"))
                .thenReturn(Optional.of(Alert.builder().createdAt(LocalDateTime.now().minusMinutes(16)).build()));

        assertTrue(service.processAlert(1L, 7L, "ML_ANOMALY", "anomaly", 0.4, 0.9, "owner@example.test"));

        verify(emailService, times(1)).sendEmail(eq("owner@example.test"), any(), any());
    }

    @Test
    void keepsDifferentUsersIndependentEvenWhenDeviceIdsMatch() {
        EmailService emailService = mock(EmailService.class);
        AlertRepository repository = mock(AlertRepository.class);
        AlertContextClient contextClient = mock(AlertContextClient.class);
        AlertMetrics alertMetrics = mock(AlertMetrics.class);
        AlertService service = new AlertService(emailService, repository, contextClient, alertMetrics, true, 15);
        when(repository.save(any(Alert.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(emailService.sendEmail(any(), any(), any())).thenReturn(true);
        when(repository.findTopByDeduplicationKeyOrderByCreatedAtDesc(any())).thenReturn(Optional.empty());

        assertTrue(service.processAlert(1L, 7L, "ML_ANOMALY", "a", 0.4, 0.9, "one@example.test"));
        assertTrue(service.processAlert(2L, 7L, "ML_ANOMALY", "b", 0.4, 0.9, "two@example.test"));

        verify(emailService, times(2)).sendEmail(any(), any(), any());
    }

    @Test
    void recordsAnUnsentAlertAndEmitsFailureMetricWhenEmailDeliveryFails() {
        EmailService emailService = mock(EmailService.class);
        AlertRepository repository = mock(AlertRepository.class);
        AlertContextClient contextClient = mock(AlertContextClient.class);
        AlertMetrics alertMetrics = mock(AlertMetrics.class);
        AlertService service = new AlertService(emailService, repository, contextClient, alertMetrics, true, 15);
        org.mockito.ArgumentCaptor<Alert> savedAlerts = forClass(Alert.class);

        when(repository.findTopByDeduplicationKeyOrderByCreatedAtDesc("1:7:THRESHOLD"))
                .thenReturn(Optional.empty());
        when(repository.save(any(Alert.class))).thenAnswer(invocation -> invocation.getArgument(0));
        when(emailService.sendEmail(anyString(), anyString(), anyString())).thenReturn(false);

        assertTrue(service.processAlert(
                1L, 7L, "THRESHOLD", "Threshold exceeded", 25.0, 31.5, "owner@example.test"));

        verify(repository, times(2)).save(savedAlerts.capture());
        Alert persistedAlert = savedAlerts.getAllValues().get(1);
        assertFalse(persistedAlert.isSent());
        assertEquals("1:7:THRESHOLD", persistedAlert.getDeduplicationKey());
        verify(alertMetrics).created("THRESHOLD");
        verify(alertMetrics).deliveryFailed("THRESHOLD");
    }
}
