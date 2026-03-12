# IOT Hackathon 2026 - Mannings Store Pickup SLA Optimization
## Stage 1 Initial Proposal

**Team Name:** ESGenius  
**Submission Date:** February 15, 2026  
**Challenge:** DFI Retail Group - Mannings Store Pickup SLA Optimization

---

## 1. Objectives

### Project Vision

Build an **end-to-end Store Pickup SLA Optimization System** for Mannings, integrating AI/ML prediction with mathematical optimization:

> **"Ensure every customer picks up their order within the promised time, while maximizing efficiency and minimizing costs"**

### Target KPIs

| Metric | Target Improvement |
|--------|-------------------|
| SLA Achievement Rate | Increase from current baseline |
| Forecast Accuracy (MAPE) | Reduce prediction error |
| Delivery Efficiency | Optimize route distance |
| Stockout Rate | Reduce inventory gaps |
| Pickup Promise Accuracy | Improve time window precision |

### Strategic Goals

1. **Customer Experience**: Reliable "Ready for Pickup" time promises
2. **Operations Intelligence**: Data-driven automated decisions
3. **Cost Optimization**: Minimize fleet & inventory costs while maintaining SLA
4. **Scalability**: Modular architecture for future expansion

---

## 2. Pain Points / Problems to Address

Based on the **Mannings Challenge Briefing (A-E five core problems)**:

| Problem | Key Challenge | Our Solution |
|---------|---------------|--------------|
| **A. Demand Fluctuation** | Promotions, long-tail SKUs, seasonality | Prophet + Weather + Promotion Calendar |
| **B. Inventory Uncertainty** | Book stock ≠ Actual, multi-channel competition | Available-to-Promise (ATP) Model |
| **C. Replenishment Delays** | DC→ECDC lead time uncertainty | Scenario-based Robust Planning |
| **D. Fleet Scheduling** | Time windows, capacity, SLA vs cost | Robust CVRPTW Optimization |
| **E. Store Processing** | Picking/packing time variance | Probabilistic Prediction |

### Problem Details

**A. Demand Fluctuation** - Promotions can cause significant demand spikes; long-tail SKUs have high variance; weather affects seasonal products. We integrate external features into Prophet forecaster.

**B. Inventory Uncertainty** - Multi-channel sales compete for same inventory with synchronization delays. Our ATP model provides dynamic safety stock calculation.

**C. Replenishment Delays** - DC→ECDC lead time varies with uncertain capacity. We use robust optimization for worst-case scenarios.

**D. Fleet Scheduling** - Traditional routing assumes fixed demand; we use scenario-based approach to handle uncertainty.

**E. Store Processing Time** - Varies by staff experience, order complexity, and time of day. Our probabilistic predictor outputs confidence intervals.

---

## 3. Proposed Solution

### Innovation: End-to-End Coupled Optimization

Unlike traditional approaches that optimize each module independently, our system implements **end-to-end coupling** where:

| Traditional Approach | Our End-to-End Approach |
|---------------------|-------------------------|
| Forecast → Fixed numbers | Forecast → Confidence intervals |
| Inventory optimized separately | Inventory linked to routing constraints |
| Routing uses single demand | Routing uses demand scenarios |
| SLA estimated after planning | SLA integrated into optimization objective |

**Key Innovation Points:**

1. **Forecast-to-Decision Pipeline**: Prediction uncertainty directly drives routing decisions
2. **Closed-Loop Feedback**: SLA outcomes feed back to improve forecasts
3. **Joint Optimization**: Demand, inventory, and routing optimized together, not sequentially

### System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: Frontend (Vue3 + uniapp)                          │
│  Login | Dashboard | Forecast | Planning | SLA Alerts       │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2: API Service (FastAPI)                             │
│  RESTful Endpoints: Auth | Dashboard | Forecast | Planning  │
├─────────────────────────────────────────────────────────────┤
│  LAYER 3: Core Algorithms                                   │
│  • Demand Forecaster (Prophet)                              │
│  • Inventory Optimizer (Safety Stock)                       │
│  • Robust Router (CVRPTW + Min-Max)                         │
│  • SLA Predictor (Probabilistic)                            │
│  • Scenario Generator (Quantile/MC)                         │
├─────────────────────────────────────────────────────────────┤
│  LAYER 4: AI Agents (Stage 2)                               │
│  Multi-Agent Coordinator                                    │
├─────────────────────────────────────────────────────────────┤
│  LAYER 5: Data Layer                                        │
│  Store/Order Data | External: HKO, data.gov.hk, CSDI        │
└─────────────────────────────────────────────────────────────┘
```

### Core Innovation: Robust Routing Optimizer

Traditional routing assumes known demand; we use scenario-based approach:

**Step 1 - Scenario Generation:**
- Quantile scenarios: P10 (low), P50 (median), P90 (high)
- Ratio scenarios: 0.9x, 1.0x, 1.1x
- Monte Carlo sampling

**Step 2 - Multi-Scenario Solving:**
- Run OR-Tools CVRPTW for each scenario
- Record routes, distance, time, SLA risk

**Step 3 - Robust Selection:**
- Min-Max criterion: Select route with best worst-case performance

### Algorithm Implementation

```python
from scenario_generator import ScenarioGenerator
from robust_optimizer import RobustOptimizer

# Generate demand scenarios from forecast confidence intervals
scenarios = ScenarioGenerator(
    quantile_keys={"low": "p10", "mid": "p50", "high": "p90"},
    monte_carlo_samples=5
).generate(forecast_data)

# Solve all scenarios and select robust solution
optimizer = RobustOptimizer(demand_ratios=[0.9, 1.0, 1.1])
solutions = optimizer.solve_all_scenarios(scenarios)
robust_plan = optimizer.select_robust_solution(criterion="min_max_distance")
```

### End-to-End Data Flow

```
Historical Data + External Features
        ↓
Prophet Forecaster → Demand with Confidence Intervals
        ↓
Scenario Generator → Multiple Demand Scenarios
        ↓
Robust Optimizer → Optimal Routes (Min-Max Selection)
        ↓
SLA Predictor → Pickup Time Promise with Confidence
        ↓
Customer Promise → Reliable pickup time notification
```

---

## 4. Data Sources

### Official Hong Kong Open Data (Required)

**HKO Weather API** - Primary External Dataset

| Data Element | Description | Application |
|--------------|-------------|-------------|
| Weather Forecast | Temperature, humidity, rainfall | Seasonal demand adjustment |
| Current Weather | Real-time conditions | Same-day delivery estimation |
| Weather Warnings | Typhoon, rainstorm signals | SLA contingency planning |
| Historical Data | Past weather patterns | Model training features |

**data.gov.hk - Supplementary Datasets**

| Dataset | Description | Application |
|---------|-------------|-------------|
| Public Holidays | Government holiday calendar | Demand spike prediction |
| Traffic Flow | Real-time traffic conditions | Travel time estimation |

**CSDI (Common Spatial Data Infrastructure)**

| Data Element | Application |
|--------------|-------------|
| Road Network | Distance matrix calculation |
| Geolocation | Store/DC coordinate mapping |

### Data Governance Framework

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA GOVERNANCE                           │
├─────────────────────────────────────────────────────────────┤
│  Data Quality                                                │
│  ├── Validation: Schema checks, range validation            │
│  ├── Cleaning: Missing value imputation, outlier detection  │
│  └── Monitoring: Data drift detection alerts                │
├─────────────────────────────────────────────────────────────┤
│  Data Pipeline                                                │
│  ├── Ingestion: API polling, batch imports                  │
│  ├── Transformation: Feature engineering, normalization     │
│  └── Storage: Structured database + Cache layer             │
├─────────────────────────────────────────────────────────────┤
│  Data Security                                                │
│  ├── Access Control: Role-based permissions                 │
│  ├── Encryption: At-rest and in-transit                     │
│  └── Audit: Access logging for compliance                   │
└─────────────────────────────────────────────────────────────┘
```

### Challenge Data (Stage 2)

Upon receiving Mannings operational data:

| Data Type | Description |
|-----------|-------------|
| Store Information | Locations, operating hours, capacity |
| Order History | Historical demand patterns, SKU-level data |
| Inventory Data | Current stock levels, safety stock requirements |
| Fleet Information | Vehicle capacity, availability, driver schedules |

---

## 5. Benefits & Impacts

### Expected Improvements

| Metric | Expected Impact |
|--------|-----------------|
| SLA Achievement | Improvement through better demand forecasting and route optimization |
| Delivery Distance | Reduction through optimized routing algorithms |
| Vehicle Utilization | Improvement through better capacity planning |
| Stockout Rate | Reduction through improved demand prediction |
| Planning Time | Reduction from manual to automated planning |

### Environmental Impact

| Factor | Contribution |
|--------|--------------|
| Route Optimization | Reduced delivery distance → Lower fuel consumption |
| Fleet Efficiency | Better vehicle utilization → Fewer trips required |
| Carbon Footprint | Supports DFI's ESG and sustainability commitments |

### Customer Experience Improvements

| Before | After |
|--------|-------|
| Uncertain pickup times | Reliable time promises with confidence intervals |
| Long waiting at store | Reduced wait times through better planning |
| No proactive communication | Real-time alerts via mobile app |
| Frustration from delays | Proactive delay notifications |

### Operational Efficiency

| Before | After |
|--------|-------|
| Manual planning | Automated planning |
| Limited visibility | Real-time dashboard across all stores |
| Reactive problem solving | Early exception detection |
| Siloed information | Integrated view: inventory + routing + SLA |

---

## 6. Commercial Potential & Feasibility

### Phased Implementation Roadmap

```
┌─────────────────────────────────────────────────────────────┐
│                    IMPLEMENTATION PHASES                     │
├─────────────────────────────────────────────────────────────┤
│  PHASE 1: Core MVP                                           │
│  ├── Demand forecasting module (Prophet)                     │
│  ├── Basic routing optimization (OR-Tools)                   │
│  └── Simple dashboard for KPI visualization                  │
│  Deliverable: Working prototype with simulated data          │
├─────────────────────────────────────────────────────────────┤
│  PHASE 2: Integration                                        │
│  ├── HKO weather API integration                             │
│  ├── data.gov.hk holiday data integration                    │
│  ├── Robust routing with scenario optimization               │
│  └── SLA prediction module                                   │
│  Deliverable: Pilot deployment                               │
├─────────────────────────────────────────────────────────────┤
│  PHASE 3: Scale & Refine                                     │
│  ├── Full fleet integration                                  │
│  ├── Real-time tracking and alerts                           │
│  ├── Performance monitoring and model retraining             │
│  └── Mobile app for store operations                         │
│  Deliverable: Production deployment                          │
├─────────────────────────────────────────────────────────────┤
│  PHASE 4: AI Agents & Expansion                              │
│  ├── Multi-agent orchestration                               │
│  ├── Cross-region replication                                │
│  └── Advanced analytics and recommendations                  │
│  Deliverable: Scalable platform for DFI group                │
└─────────────────────────────────────────────────────────────┘
```

### Resource Requirements

| Resource | Phase 1 | Phase 2 | Phase 3 |
|----------|---------|---------|---------|
| Developers | Small team | Medium team | Full team |
| Data Scientists | Part-time | Full-time | Full-time |
| Cloud Infrastructure | Minimal | Moderate | Production |

### Replicability - Expansion Potential

**Within DFI Group:**
- Same architecture applicable to other DFI brands (Wellcome, 7-Eleven)
- Modular design allows brand-specific customization
- Shared infrastructure reduces marginal cost

**Cross-Industry Applications:**

| Industry | Use Case | Adaptation Required |
|----------|----------|---------------------|
| Grocery Retail | Fresh food delivery | Add perishability constraints |
| F&B | Restaurant supply chain | Modify time windows |
| Healthcare | Pharmacy delivery | Add compliance requirements |
| E-commerce | Last-mile delivery | Scale volume handling |

**Key Success Factors for Replication:**
1. Standardized data interfaces (REST API)
2. Configurable optimization parameters
3. Modular algorithm components
4. Cloud-native deployment

### Risk Mitigation

| Risk | Mitigation Strategy |
|------|---------------------|
| Data quality issues | Validation pipeline + fallback rules |
| Model performance degradation | Continuous monitoring + retraining triggers |
| System downtime | Redundant infrastructure + manual fallback |
| User adoption | Training program + intuitive UI |

---

## Declaration

- This proposal is an original work by Team ESGenius
- Uses official public data sources: **HKO, data.gov.hk, CSDI**
- All team members participate only in this team
- Maximum 6 members per team requirement satisfied

**GitHub:** https://github.com/iot-hackathon-2026-teamESGenius/iot_hackathon_2026_mannings

---

# Appendix: Team Profile (Not counted in page limit)

## Team ESGenius (6 Members)

| Name | Major | Role | Responsibilities |
|------|-------|------|------------------|
| Yechen WANG | CS | Lead / Architect | Architecture, routing algorithm, proposal |
| Shuang LENG | CS | Routing Dev | CVRPTW, robust optimizer, OR-Tools |
| Simin XIAN | CS | Forecasting Dev | Prophet, inventory optimization |
| Taiyi LI | DS | Data Engineer | Official data, forecasting support |
| Cong TAN | DS | Data Engineer | Data integration, simulation |
| Yu FU | CS | Visualization | Dashboard, demo |

## Team Strengths

- Cross-disciplinary: CS + Data Science combination
- Full-stack capability: Backend algorithms + Frontend visualization
- Domain expertise: Operations research, machine learning, supply chain

## Timeline

| Phase | Period | Deliverables |
|-------|--------|--------------|
| Stage 1 | Feb 1-15, 2026 | Proposal, architecture, prototypes |
| Stage 2 | Feb 16 - Mid Mar | Data integration, refinement |
| Final | Late Mar | Testing, demo, submission |
