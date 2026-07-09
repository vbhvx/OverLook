# Data Policy & Analytical Safety Guidelines

## Purpose

OverLook is built strictly as an analytical situational-awareness platform for exploring public, authorized, and appropriately licensed geospatial signals. It is designed to understand regional patterns, natural events, and public infrastructure status.

## Prohibited Capabilities & Strict Boundaries

The following capabilities are explicitly out of scope and prohibited by architectural design:

1. **No Individual Surveillance or Dossier Generation**:
   - The platform does not track private individuals, infer their personal routines, or correlate personal identities with locations.
2. **No Biometric or Facial Recognition**:
   - Public camera feeds are limited to authorized municipal traffic and roadway condition monitoring. No facial recognition or human tracking algorithms are integrated.
3. **No Private CCTV Scraping or Authentication Bypasses**:
   - OverLook only integrates documented, publicly broadcast feeds provided by government transportation agencies (e.g., Caltrans, WSDOT). Private security cameras or undocumented IP camera links are prohibited.
4. **No Vulnerability Targeting**:
   - Infrastructure data is restricted to open geographic landmarks (airports, maritime ports, suspension bridges, seismic arrays). The platform will not model non-public access routes, defensive perimeters, or security vulnerabilities.
5. **No Speculative Causality**:
   - Proximity is not causation. OverLook never asserts that an aircraft, vessel, or satellite pass is causally connected to an event solely because of geographic closeness. All cross-layer associations are explicitly labeled as hypotheses or spatial-temporal co-occurrences.
6. **No Fabricated Real-Time Signals**:
   - The system never fabricates real-time positions. When simulated fixtures are loaded for demonstrator purposes, they are permanently tagged with `isSimulated: true` and `dataStatus: "simulated"`.

