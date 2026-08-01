# ByteFlow - example commands to try

Run these one at a time from wherever `byteflow` works on your machine
(e.g. `D:\ByteFlow>`). Replace the DataLab path with wherever yours
actually is.

## 1. Math (built-in tool, no LLM needed for the actual calculation)
```
byteflow run "add 10 and 20"
```

## 2. Weather (real API, not a guess)
```
byteflow run "weather in ahmedabad today"
```

## 3. Web search (real DuckDuckGo results, summarized)
```
byteflow run "latest news on AI"
```

## 4. Code generation + execution
```
byteflow run "write a python function that checks if a number is prime"
```

## 5. Open/launch an app or file
```
byteflow run "open notepad"
```

## 6. DataLab - price prediction for an EXISTING car in the dataset
```
byteflow run "show me price predictions for some cars in the data" --extension-path D:\MachineLearning\DataLab
```

## 7. DataLab - price prediction for a NEW hypothetical car
```
byteflow run "predict car price 2028 which runs 10000km" --extension-path D:\MachineLearning\DataLab
```

---

## Bonus - a few more worth trying

**Today's date/time (instant, no LLM call):**
```
byteflow run "what is today's date"
```

**DataLab - dataset overview:**
```
byteflow run "give me an overview of the car data" --extension-path D:\MachineLearning\DataLab
```

**DataLab - find outliers:**
```
byteflow run "find outliers in the car price data" --extension-path D:\MachineLearning\DataLab
```

**Plain chat (no tool needed):**
```
byteflow run "hii"
```

**See what ByteFlow has learned about you:**
```
byteflow profile
```

**Launch the GUI companion instead of one-off commands:**
```
byteflow companion --extension-path D:\MachineLearning\DataLab
```
