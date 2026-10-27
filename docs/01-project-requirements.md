# Project Requirements Document

## Project Name

Home Energy Tracker

## Goal

Build a cloud-deployed, event-driven platform that helps households understand electricity consumption, estimate their monthly bill, identify high-consuming appliances, and receive actionable energy-saving alerts.

The project must retain its advanced microservices architecture: services communicate through APIs and Kafka events, time-series energy data is stored in InfluxDB, and the application is deployed as Docker containers.

## Target Users

- Households that want visibility into appliance-level electricity usage.
- Students, reviewers, and recruiters evaluating a production-style cloud and microservices project.
- A project administrator/demo user who can use simulated readings before real smart-meter hardware is available.

## Problem Statement

Electricity bills usually arrive after the consumption has already happened. Most users cannot see which appliance is responsible for high usage or detect unnecessary standby consumption in time to act.

## Core Features

### User and device management

- Create and manage household user profiles.
- Add appliances with a name, type, power rating, and optional usage threshold.
- View a user's registered appliances.

### Energy ingestion and event processing

- Accept an energy reading for a device through an ingestion API.
- Publish each valid reading to Kafka.
- Process usage events asynchronously in the Usage Service.
- Support the existing simulator as a demo data source; physical smart plugs/meters are a future input source.

### Usage analytics

- Store timestamped readings in InfluxDB.
- Show usage for the selected user, appliance, and time range.
- Calculate total kWh and rank appliances by consumption.

### Bill forecast and saving insights

- Estimate the current billing-period cost using configurable tariff slabs/rates.
- Forecast month-end consumption and bill from the current consumption rate.
- Provide concise, evidence-based savings recommendations.
- Keep AI-generated language optional: core bill calculations must work if the AI service is unavailable.

### Novel MVP feature: Standby Energy Detective

- Calculate a household's low-activity/night-time baseline consumption.
- Flag an abnormal baseline as probable standby/phantom load.
- Explain the estimated monthly units and cost that could be saved.
- Suggest likely device categories to check, without claiming a specific device is at fault unless device-level data supports it.

### Alerts

- Trigger an alert when a device or household crosses its configured usage threshold.
- Send an email notification in deployed environments.
- Record alert history for the user.

### Dashboard and operations

- Provide a responsive web dashboard for the core user flow.
- Provide Swagger/OpenAPI for backend testing.
- Expose health and metrics endpoints for operational monitoring.

## Out of Scope for Version 1

- Direct switching/control of appliances.
- Native mobile applications.
- Utility-provider billing integration.
- Guaranteed appliance identification from only one aggregate meter reading.
- Multi-tenant enterprise energy management.
- Training a custom machine-learning model.

## Success Criteria

- A demo user can add devices, submit/simulate readings, and see usage within the dashboard.
- A reading follows the full ingestion-to-Kafka-to-usage-storage path.
- The dashboard displays total consumption, top-consuming device, estimated bill, and forecast.
- The Standby Energy Detective displays a result when sufficient low-activity data exists.
- A configured threshold produces a stored alert and a deployable email notification.
- The full stack can run locally with Docker Compose and on the selected Azure Linux VM.
- The public deployment uses HTTPS, secrets are not committed, and only the gateway/reverse proxy is internet-facing.

