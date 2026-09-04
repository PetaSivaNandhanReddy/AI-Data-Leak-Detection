# 🛡️ AI-Powered Data Leak Detection and Alerting System

## Using NLP, Machine Learning and Hybrid RSA-AES Encryption

### 📌 Overview

This project presents an AI-powered data leak detection and alerting system designed to identify sensitive information in user-generated text such as social media posts and messages.

The system combines multiple detection techniques:

- Regular Expression (Regex) based PII detection
- Natural Language Processing (NLP)
- spaCy Named Entity Recognition (NER)
- TF-IDF feature extraction
- Logistic Regression classification
- Hybrid RSA-AES encryption
- Interactive Gradio and Streamlit interfaces

When a potential data leak is detected, the system generates an alert and protects the alert information using hybrid encryption.

---

## 🎯 Objectives

The main objectives of the project are:

- Detect sensitive information in text-based posts.
- Identify Personally Identifiable Information (PII).
- Use NLP to understand contextual entities.
- Classify posts as `Leak` or `Non-Leak`.
- Combine rule-based and machine-learning detection.
- Secure detected alerts using encryption.
- Provide an interactive interface for real-time testing.

---

## 🧠 System Architecture

The system follows a multi-stage pipeline:

```text
User Input
    ↓
Text Preprocessing
    ↓
 ┌───────────────┬────────────────┬─────────────────┐
 │               │                │                 │
Regex Detection  spaCy NER    TF-IDF + ML
 │               │                │
 └───────────────┴────────────────┘
                 ↓
        Hybrid Decision Logic
                 ↓
       Leak / No-Leak Decision
                 ↓
          If Leak Detected
                 ↓
       Alert Generation
                 ↓
       AES-256 Encryption
                 ↓
       RSA-2048 Key Encryption
                 ↓
       SHA-256 Integrity Check
                 ↓
       Secure Alert Output
