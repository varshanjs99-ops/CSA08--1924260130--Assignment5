# Assignment 5 - Part A Design

## A5 - Design an AI Application for Citizen Complaints (4 marks)

### A5.1 Sentiment and summary

Use a transparent word-list sentiment baseline. Positive words add +1, negative words add -1, and a directly preceding negator flips the next sentiment word. Two adjacent negators cancel under the simple parity rule. The total above zero is positive, below zero is negative and zero is neutral. The approach is easy to explain and fast, but sarcasm, implicit meaning, domain terms and long-range grammar can cause errors.

For extractive summarisation, split complaints into sentences, remove common stop words, count informative word frequencies and score each sentence using the frequencies of its terms. Select the highest-scoring sentences while preserving their original text. A first-k-sentence baseline is constant-time selection after sentence splitting but may miss important topics; frequency scoring takes O(w) over w tokens plus ranking cost and needs a word-frequency map.

### A5.2 Basic chatbot

The rule-based chatbot detects a station name and a requested measure (PM2.5, PM10, NO2 or temperature), extracts an explicit date when supplied, or uses the latest available date in the sample database. It submits a parameterised SQL query and explains when no data is available. The latest sample date must not be presented as the real current date. This chatbot is retrieval-based, not generative.

**Chatbot pseudocode:**

```text
ALGORITHM AnswerCitizenAirQualityQuestion
BEGIN
    INPUT citizen_question
    IDENTIFY requested pollutant and station name
    IDENTIFY explicit date; otherwise select latest date available in sample data
    IF pollutant or station cannot be identified THEN
        RETURN a request for a supported pollutant/station
    END IF
    EXECUTE a parameterised SQL query for station, date and pollutant
    IF no valid reading exists THEN
        RETURN a no-data message
    ELSE
        RETURN the computed average with date and measurement unit
    END IF
END
```

A trained Naive Bayes classifier or a suitable language model could better recognise context, sarcasm and local complaint language if trained/evaluated on labelled local examples. It requires labelled data, model storage, validation and monitoring. A pre-trained language model generally uses more memory and compute per complaint than a small lexicon, and may still hallucinate or misread local references. Keep the simple model as a transparent baseline and human-review uncertain complaints.
