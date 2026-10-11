# ByteFlow - Issues & Performance Improvements

## 🔴 CRITICAL ISSUES

### 1. Conversation Mode Slowness (companion.py:1077-1149)
**Problem:** GUI freezes while loading Vosk model
**Solution:** 
```python
# Before (blocking):
conv.start()  # Freezes UI

# After (non-blocking):
threading.Thread(target=conv.start, daemon=True).start()
```

### 2. Synchronous Agent Processing (companion.py:62-79)
**Problem:** Long-running LLM calls block the message queue
**Impact:** "still thinking..." message never appears; UI seems frozen
**Solution:** Implement request timeout + progress indicators

```python
# Add to CompanionController._run()
def _run(self, message):
    def worker():
        try:
            # Set 30-second timeout for inference
            result = timeout_wrapper(
                self.agent.run, 
                args=(message,),
                timeout=30
            )
```

---

## ⚠️ SMALL ERRORS TO FIX

### Issue 1: File Reading Edge Case (file_reading.py:48-80)
- **Bug:** Image-only PDFs throw unclear error
- **Fix:** Already handled! Error message is clear
- **Status:** ✅ GOOD

### Issue 2: Intent Classification Too Conservative (intent_classifier.py:23-30)
- **Problem:** 0.28 confidence threshold misses valid intents
- **Recommendation:** Increase to 0.35 for better recall
- **File:** `byteflow/intent_classifier.py` line 23

### Issue 3: Weather Lookup Fragile (weather.py:80-168)
- **Problem:** Single network failure breaks entire request
- **Fix:** Add retry logic
```python
@retry(max_attempts=3, backoff_factor=1.5)
def _get_json(url, params):
    # existing code
```

---

## 🚀 SPEED OPTIMIZATIONS

### 1. Async Model Inference
**Current:** Synchronous blocking calls  
**Improvement:** Use `asyncio` or thread pooling for:
- Weather lookups
- Web searches
- File I/O operations

### 2. Response Caching
- Cache frequent queries (weather for same location, etc.)
- Use `functools.lru_cache` on weather functions

### 3. Model Preloading
- Preload the Vosk model on startup (not first use)
- Cache intent classifier on launch

### 4. Conversation Mode Enhancements
- Add background voice activity detection
- Implement voice silence timeout (auto-stop after 2s silence)
- Buffer incomplete sentences instead of sending immediately

---

## 📋 ACTION ITEMS

- [ ] Add timeout wrapper to agent.run()
- [ ] Implement async version of weather API
- [ ] Add retry decorator to network requests
- [ ] Pre-load Vosk model at startup
- [ ] Add progress/typing indicator during LLM processing
- [ ] Implement request prioritization queue
- [ ] Add metrics logging (response times, error rates)
