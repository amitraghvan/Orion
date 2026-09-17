# ORION Voice Alert System Audit

**Project:** ORION — AI Human Activity Recognition for On-board BAS Experiments (SIH26174)  
**Organization:** Indian Space Research Organisation (ISRO)  
**Date:** September 17, 2026  
**Status:** IMPLEMENTED & VERIFIED  

---

## 1. Architectural Overview & Air-Gapped Offline Execution

The Voice Alert System is implemented in [`app/audio/tts_engine.py`](file:///Users/amitkumar/Orion/app/audio/tts_engine.py) and [`backend/src/orion/audio/`](file:///Users/amitkumar/Orion/backend/src/orion/audio/).

### Critical Air-Gap Compliance Check:
- **Cloud Dependency Check:** **ZERO.** No calls to Google Cloud Text-to-Speech, ElevenLabs, OpenAI Audio, or AWS Polly.
- **Offline Speech Providers:**
  1. **Cross-Platform:** `pyttsx3` offline speech synthesis engine (uses SAPI5 on Windows, NSSpeechSynthesizer on macOS, eSpeak on Linux).
  2. **macOS Native Fallback:** System CLI utility `/usr/bin/say`.
  3. **Linux Native Fallback:** System CLI utility `/usr/bin/espeak` or `/usr/bin/espeak-ng`.
- **Runtime Execution:** Operates completely within an independent background worker thread (`TTSWorkerThread`), ensuring audio rendering never blocks the 30 FPS video pipeline.

---

## 2. Queueing, Priority Preemption & Anti-Spam Cooldown

Astronaut operations inside microgravity gloveboxes produce continuous sensor readings. Without suppression, speech synthesis would rapidly queue up repetitive alerts. ORION enforces 4 safety layers:

```
Incoming Speech Request ("Warning. Out of sequence.")
                  │
                  ▼
         [Duplicate Check] ──► Text matches last utterance within cooldown?
                  │            YES: Utterance dropped (anti-spam suppression)
                  ▼ NO
         [Priority Queue]
           Priority 1: Safety Violations (Wrong object, Out of sequence)
           Priority 2: Mission Events (Experiment complete, Failure)
           Priority 3: Procedural Guidance (Step completed, Next step)
                  │
                  ▼
         [Worker Dispatch] ──► Speech synthesis executed asynchronously
```

### Priority Hierarchy
- **Priority 1 (Emergency / Violation):** High-priority alerts preempt lower-priority messages. (e.g., *"Warning. Wrong object manipulated."*)
- **Priority 2 (Milestone):** Significant state transitions. (e.g., *"Experiment completed successfully. All steps verified."*)
- **Priority 3 (Procedural Guidance):** Step progression cues. (e.g., *"Step 2 completed. Please perform Step 3."*)

### Cooldown Suppression Invariant
- A cooldown timer ($\Delta t = 3.0 \text{ s}$) prevents identical utterances from repeating consecutively.
- Forced utterances (`force=True`) bypass the cooldown filter for urgent operator notifications.

---

## 3. Verified Utterance Catalog

| Trigger Event | Priority | Synthesized Voice Utterance |
|---|---|---|
| Experiment Started | 3 | `"Experiment started. Please perform Step 1."` |
| Nominal Step Advance | 3 | `"Step {k} completed. Please perform Step {k+1}."` |
| Out of Sequence Step | 1 | `"Warning. Out of sequence activity detected."` |
| Wrong Object Manipulated | 1 | `"Warning. Wrong object manipulated."` |
| Procedural Interruption | 1 | `"Warning. Procedural sequence interrupted."` |
| Experiment Finalized | 2 | `"Experiment completed successfully. All steps verified."` |
| Manual Run Abort | 2 | `"Experiment aborted by operator."` |
