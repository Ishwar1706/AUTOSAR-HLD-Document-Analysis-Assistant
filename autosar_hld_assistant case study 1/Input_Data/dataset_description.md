# Input Data — Dataset Description

## Overview

This project uses three synthetic AUTOSAR High-Level Design (HLD) PDF documents created specifically for pilot evaluation. These documents are **NOT** derived from any real automotive program or proprietary data.

## Documents

| Document | Domain | Version | Pages | Description |
|----------|--------|---------|-------|-------------|
| HLD_BCM_v1.0.pdf | Body Control Module | 1.0 | 5 | Central locking, exterior lighting, wiper control, window lift |
| HLD_ADAS_FCW_v1.0.pdf | ADAS Forward Collision Warning | 1.0 | 5 | Sensor fusion, collision risk estimation, warning arbitration |
| HLD_BMS_v1.1.pdf | Battery Management System | 1.1 | 5 | Cell monitoring, thermal management, contactor control, balancing |

## Document Structure

Each document follows a standard AUTOSAR HLD format:
1. Document Control
2. Introduction and Scope
3. Software Component Overview (table)
4. Ports and Interfaces (table)
5. Signals and Data Elements (table)
6. Component Dependencies (table)
7. Functional Flow (numbered sequence)
8. Assumptions and Open Points
9. Revision History

## Entity Counts (Ground Truth)

| Document | Components | Interfaces | Signals |
|----------|-----------|------------|---------|
| HLD_BCM_v1.0.pdf | 4 | 8 | 8 |
| HLD_ADAS_FCW_v1.0.pdf | 4 | 9 | 8 |
| HLD_BMS_v1.1.pdf | 5 | 9 | 6 |

## Data Location

Sample documents are stored in `sample_docs/` and can be loaded via the Dashboard's "Ingest All Sample Documents" button.

## Important Note

All data in these documents is synthetic. No real vehicle program data, calibration values, or proprietary information is included. Any resemblance to actual automotive systems is intentional for realism but does not represent any specific vehicle program.
