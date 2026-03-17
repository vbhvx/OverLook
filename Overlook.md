# Technical Specification: Public Signal Intelligence & Situational Awareness Platform

**Project type:** Full-stack geospatial engineering challenge  
**Product category:** OSINT · Geospatial Intelligence · Real-Time Data Integration  
**Initial scope:** Global map with configurable geographic regions and multiple public-signal layers  
**Data categories:** Aircraft · Ships · Satellites · Earthquakes · Weather · Public Cameras · Infrastructure  
**Architecture:** React + TypeScript · Python + FastAPI · PostgreSQL + PostGIS · MapLibre GL JS  
**Delivery approach:** Phased implementation with verifiable data, source-aware visualization, and explicit integration boundaries

## Objective

Build a responsive geospatial intelligence application that consolidates public, authorized, and appropriately licensed real-world signals into a unified interactive map.

The application should help users understand what is happening in a geographic area by exploring multiple independent layers, examining the original evidence, reviewing timelines, and understanding relationships between signals.

Instead of switching between separate aircraft trackers, ship trackers, satellite dashboards, earthquake feeds, weather services, public camera directories, and infrastructure maps, users should have one coherent workspace for exploring these sources.

The platform must not merely place unrelated datasets on the same map. It should normalize their spatial and temporal information, communicate their provenance and freshness, preserve the differences between data types, and help users investigate potentially related events without presenting speculation as established fact.

**Priority order:** source verification → data correctness → spatial and temporal normalization → trustworthy multi-layer visualization → useful cross-source exploration → event correlation → responsive performance → testing → deployment.

The result should be an analytical situational-awareness platform, not a system for targeting individuals, enabling unauthorized surveillance, or making unsupported claims about real-world events.

---

## 1. Scope and acceptance criteria

