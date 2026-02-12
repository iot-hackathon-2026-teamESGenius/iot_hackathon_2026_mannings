# IOT Hackathon 2026 - Mannings Store Pickup SLA Optimization
# Stage 1 Initial Proposal

<p align="center">
  <strong>Store Pickup SLA Optimization System</strong><br>
  DFI Retail Group - Mannings
</p>

**Team Name:** ESGenius  
**Submission Date:** February 15, 2026  
**Challenge:** DFI Retail Group - Mannings Store Pickup SLA Optimization

---

## 1. Objectives

### 1.1 Project Vision

Build an **end-to-end Store Pickup SLA Optimization System** for Mannings, integrating AI/ML prediction with mathematical optimization:

> **"Ensure every customer picks up their order within the promised time, while maximizing efficiency and minimizing costs"**

### 1.2 Core KPIs

```mermaid
graph LR
    A[SLA Rate] -->|+10%| B[85% → 95%]
    C[Forecast MAPE] -->|Target| D[< 15%]
    E[Route Cost] -->|-20%| F[Optimized]
    G[Stockout] -->|Reduce| H[< 5%]
    I[Pickup Promise] -->|Accuracy| J[±15 min]
```

### 1.3 Strategic Goals

1. **Customer Experience**: Reliable "Ready for Pickup" time promises
2. **Operations Intelligence**: Data-driven automated decisions
3. **Cost Optimization**: Minimize fleet & inventory costs while maintaining SLA
4. **Scalability**: Modular architecture for future AI Agent expansion

---

## 2. Pain Points / Problems to Address

Based on **A-E five core problems** from the Mannings Challenge Briefing:

```mermaid
graph TB
    subgraph Problems
        A[A: Demand Fluctuation]
        B[B: Inventory Uncertainty]
        C[C: Replenishment Delays]
        D[D: Fleet Scheduling]
        E[E: Store Processing Time]
    end
    
    subgraph Solutions
        A1[Prophet + External Features]
        B1[ATP Inventory Model]
        C1[Robust Optimization]
        D1[CVRPTW + Min-Max]
        E1[Probabilistic SLA]
    end
    
    A --> A1
    B --> B1
    C --> C1
    D --> D1
    E --> E1
```

### Problem Details

| Problem | Key Challenge | Our Solution |
|---------|---------------|--------------|
| **A. Demand** | Promotions, long-tail SKUs, seasonality | Prophet + HKO weather + promotion calendar |
| **B. Inventory** | Book ≠ Actual, multi-channel competition | Available-to-Promise model with safety stock |
| **C. Replenishment** | DC→ECDC lead time uncertainty | Scenario-based robust planning |
| **D. Routing** | Time windows, capacity, SLA vs cost | **Robust CVRPTW (Core Innovation)** |
| **E. Processing** | Picking/packing time variance | Probabilistic prediction with CI |

---

## 3. Proposed Solution

### 3.1 Five-Layer System Architecture

```mermaid
graph TB
    subgraph L1[Layer 1: Frontend - Vue3 + uniapp]
        F1[Login]
        F2[Dashboard]
        F3[Forecast]
        F4[Planning]
        F5[SLA Alerts]
    end
    
    subgraph L2[Layer 2: API Service - FastAPI]
        API[RESTful API Endpoints]
    end
    
    subgraph L3[Layer 3: Core Algorithms]
        M1[Demand Forecaster<br/>Prophet]
        M2[Inventory Optimizer<br/>Safety Stock]
        M3[Robust Router ⭐<br/>CVRPTW + Min-Max]
        M4[SLA Predictor<br/>Probabilistic]
        M5[Scenario Generator<br/>Quantile/MC]
    end
    
    subgraph L4[Layer 4: AI Agents - Stage 2]
        AG[Multi-Agent Coordinator]
    end
    
    subgraph L5[Layer 5: Data Layer]
        D1[Store/Order Data]
        D2[External: HKO, Gov.hk]
    end
    
    L1 --> L2
    L2 --> L3
    L3 -.-> L4
    L3 --> L5
```

### 3.2 Core Innovation: Robust Routing Optimizer ⭐

Traditional routing optimization ignores demand uncertainty. Our **Scenario-based Robust CVRPTW** addresses this:

```mermaid
graph LR
    subgraph Step1[Step 1: Scenario Generation]
        S1[Quantile: P10, P50, P90]
        S2[Ratio: 0.9x, 1.0x, 1.1x]
        S3[Monte Carlo Sampling]
    end
    
    subgraph Step2[Step 2: Multi-Scenario Solving]
        SOLVE[OR-Tools CVRPTW<br/>per scenario]
    end
    
    subgraph Step3[Step 3: Robust Selection]
        SEL[Min-Max Strategy<br/>Best worst-case]
    end
    
    Step1 --> Step2 --> Step3
```

**Key Innovation Points:**
- **Uncertainty Quantification**: Convert forecast CI to demand scenarios
- **Min-Max Robustness**: Optimize for worst-case scenario performance
- **Forecast→Decision Loop**: Prediction uncertainty directly drives routing

### 3.3 End-to-End Data Flow

```mermaid
graph LR
    A[Historical Data<br/>+ External Features] --> B[Prophet<br/>Forecaster]
    B --> C[Scenario<br/>Generator]
    C --> D[Robust<br/>Optimizer]
    D --> E[SLA<br/>Predictor]
    E --> F[Pickup Time<br/>Promise]
    
    style D fill:#e1f5fe
```

### 3.4 Algorithm Implementation

```python
# Robust Optimization Core Logic
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

**Standardized Output Format:**
```
OptimizationResult:
  - routes: [[store_ids], ...]
  - total_distance: km
  - total_time: min
  - vehicles_used: int
  - sla_risk_score: 0-1
```

---

## 4. Data Sources

### 4.1 Data Integration Architecture

```mermaid
graph TB
    subgraph Official[Official HK Open Data ✓]
        HKO[HKO Weather API]
        GOV[data.gov.hk<br/>Holidays, Traffic]
        CSDI[CSDI Geospatial]
    end
    
    subgraph Challenge[Challenge Data - Stage 2]
        STORE[Store Info]
        ORDER[Order History]
        INV[Inventory]
        FLEET[Fleet Info]
    end
    
    subgraph Simulated[Stage 1 Dev]
        SIM[SimulatedDataFetcher]
    end
    
    Official --> CORE[Core Modules]
    Challenge --> CORE
    Simulated --> CORE
```

### 4.2 Official Data Usage

- **HKO**: Weather forecasts → Demand adjustment factors
- **data.gov.hk**: Public holidays, traffic flow → Time estimation
- **CSDI**: Road network, geolocation → Distance matrix

---

## 5. Benefits & Impacts

### 5.1 Expected Improvements

```mermaid
graph TB
    subgraph Customer[Customer Experience]
        C1[Reliable Promises]
        C2[Reduced Waiting]
        C3[Proactive Alerts]
    end
    
    subgraph Operations[Operational Efficiency]
        O1[Automated Planning]
        O2[Real-time Visibility]
        O3[Early Exception Detection]
    end
    
    subgraph Cost[Cost Control]
        CO1[Route Optimization -15%]
        CO2[Vehicle Utilization +20%]
        CO3[Stockout Reduction -40%]
    end
```

### 5.2 Quantified Benefits

| Metric | Improvement | Impact |
|--------|-------------|--------|
| SLA Achievement | +10% (85%→95%) | Customer satisfaction ↑ |
| Delivery Distance | -15% | Fuel cost savings |
| Vehicle Utilization | +20% | Fleet size reduction |
| Stockout Rate | -40% | Lost sales reduction |
| Planning Time | -80% | Hours → Minutes |

---

## 6. Technical Stack & Repository

### 6.1 Technology Overview

```mermaid
graph LR
    subgraph Backend
        PY[Python 3.9]
        FAST[FastAPI]
        ORT[OR-Tools]
        PROP[Prophet]
    end
    
    subgraph Data
        PD[Pandas]
        NP[NumPy]
        GEO[GeoPandas]
    end
    
    subgraph Viz
        ST[Streamlit]
        PLT[Plotly]
    end
    
    subgraph Frontend
        VUE[Vue 3]
        UNI[uniapp]
    end
```

### 6.2 Repository Structure

```
iot_hackathon_2026_mannings/
├── src/
│   ├── api/routers/          # FastAPI endpoints
│   ├── modules/
│   │   ├── routing/          # ⭐ Robust Optimizer
│   │   ├── forecasting/      # Prophet
│   │   ├── inventory/        # Safety Stock
│   │   └── sla/              # Probabilistic
│   └── agents/               # Stage 2 interfaces
├── config/
└── tests/
```

### 6.3 API Endpoints

| Module | Endpoint | Function |
|--------|----------|----------|
| Auth | `/api/auth/*` | Login, Token |
| Dashboard | `/api/dashboard/*` | KPI, Trends |
| Forecast | `/api/forecast/*` | Demand, Inventory |
| Planning | `/api/planning/*` | Routes, Replenishment |
| SLA | `/api/sla/*` | Orders, Alerts |

---

## Declaration

- This proposal is an **original work** by our team
- Uses official public data sources: **HKO, data.gov.hk, CSDI**
- All team members participate only in this team

**GitHub:** https://github.com/iot-hackathon-2026-teamESGenius/iot_hackathon_2026_mannings

---

# Appendix: Team Profile (Not counted in page limit)

## Team: ESGenius (6 members)

| Name | Major | Role | Responsibilities |
|------|-------|------|------------------|
| Yechen WANG | CS | Lead / Architect | Architecture, routing algorithm, proposal |
| Shuang LENG | CS | Routing Dev | CVRPTW, robust optimizer, OR-Tools |
| Simin XIAN | CS | Forecasting Dev | Prophet, inventory optimization |
| Taiyi LI | DS | Data Engineer | Official data, forecasting support |
| Cong TAN | DS | Data Engineer | Data integration, simulation |
| Yu FU | CS | Visualization | Streamlit dashboard, demo |

## Responsibility Matrix

```mermaid
graph LR
    YW[Yechen WANG] --> ARCH[Architecture]
    YW --> ROUTE[Routing]
    SL[Shuang LENG] --> ROUTE
    SX[Simin XIAN] --> FORECAST[Forecasting]
    TL[Taiyi LI] --> DATA[Data Eng]
    TL --> FORECAST
    CT[Cong TAN] --> DATA
    YF[Yu FU] --> VIZ[Visualization]
```

## Timeline

- **Stage 1** (Feb 1-15): Proposal, architecture, prototypes
- **Stage 2** (Feb 16 - Mid Mar): Data integration, refinement
- **Final** (Late Mar): Testing, demo, submission
