import React, { useEffect, useRef } from "react";
import { useTelemetryStore } from "../../store/telemetryStore";

export const VoiceAlertSystem: React.FC = () => {
  const activeViolation = useTelemetryStore((state) => state.activeViolation);
  const experimentStatus = useTelemetryStore((state) => state.experimentStatus);
  const setVoiceStatus = useTelemetryStore((state) => state.setVoiceStatus);

  const lastSpokenTextRef = useRef<string>("");
  const lastSpokenTimeRef = useRef<number>(0);

  const speak = (text: string) => {
    if (!window.speechSynthesis) return;

    const now = Date.now();
    // Debounce duplicate utterances within 4 seconds
    if (text === lastSpokenTextRef.current && now - lastSpokenTimeRef.current < 4000) {
      return;
    }

    lastSpokenTextRef.current = text;
    lastSpokenTimeRef.current = now;

    window.speechSynthesis.cancel(); // Cancel any lingering utterance

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.05;
    utterance.pitch = 1.0;
    utterance.volume = 1.0;

    utterance.onstart = () => {
      setVoiceStatus("ALERT_ACTIVE");
    };

    utterance.onend = () => {
      setVoiceStatus("READY");
    };

    utterance.onerror = () => {
      setVoiceStatus("READY");
    };

    window.speechSynthesis.speak(utterance);
  };

  // Announce violations
  useEffect(() => {
    if (!activeViolation) return;
    if (activeViolation.type === "WRONG_OBJECT") {
      speak(`Warning. Expected ${activeViolation.expected} operation.`);
    } else if (activeViolation.type === "SKIPPED") {
      speak("Step skipped. Please perform the required step.");
    } else if (activeViolation.type === "INTERRUPTED") {
      speak("Experiment procedure interrupted.");
    } else {
      speak("Experiment sequence violation detected.");
    }
  }, [activeViolation]);

  // Announce completion
  useEffect(() => {
    if (experimentStatus?.fsm_state === "COMPLETED") {
      speak("Experiment sequence completed successfully.");
    }
  }, [experimentStatus?.fsm_state]);

  return null; // Headless component providing audio synthesis
};
